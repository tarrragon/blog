---
title: "Reactive 監聽器的效能 audit：跨 listener 類型盤點觸發頻率"
date: 2026-04-25
weight: 33
description: "MutationObserver / ResizeObserver / event listener 各自的觸發頻率怎麼盤點。本文是效能 audit 視角 — 找問題用、跟 #29 (observer 設計指引) 互補不重複。"
tags: ["report", "事後檢討", "Performance", "JavaScript", "工程方法論"]
---

## 核心原則

**監聽器的「觸發頻率」是效能的第一道防線、跨多種 listener 類型一起盤點。** 本篇是 audit 視角（「我有效能問題、reactive 監聽器是不是嫌疑」）— 設計新 observer 的細節由 [#29 MutationObserver 範圍與觸發頻率](../mutation-observer-scope/) 處理。Audit 時把所有 reactive 監聽器列一張表、看哪些觸發頻率異常。

> 本篇焦點：**跨 listener 類型的效能盤點**。
> - **MutationObserver 的設計細節**（root / option / debounce / self-mutation）由 [#29](../mutation-observer-scope/) 處理
> - **Selector 範圍的設計**由 [#14](../dom-selector-precision/) 處理
> - **Runtime 計算成本**（regex / textContent / forEach）由 [#34](../runtime-iteration-and-regex-cost/) 處理

---

## 為什麼觸發頻率主導效能

### 商業邏輯

Reactive 監聽器有三個獨立成本：

| 成本來源              | 單次量級        | 累積方式     |
| --------------------- | --------------- | ------------ |
| 觸發頻率              | 看範圍與 option | 倍數疊加     |
| Callback 內部運算     | 看實作          | 每次完整跑   |
| Callback 引發的副作用 | 看 DOM 變動     | 可能反向觸發 |

把單次 callback 從 5ms 優化到 2ms 是 2.5x；把觸發次數從 100 次/秒降到 10 次/秒是 10x。**觸發頻率優化的天花板更高** — audit 時優先看頻率。

### 三類觸發頻率風險（速覽）

| 類型                         | 表現                         | 詳細處理                                               |
| ---------------------------- | ---------------------------- | ------------------------------------------------------ |
| 範圍過寬（observer subtree） | 無關變動也觸發               | [#29 root 與 option 設計](../mutation-observer-scope/) |
| Option 全勾                  | 多種變動類型同時觸發         | [#29 三維度收斂](../mutation-observer-scope/)          |
| 自激迴圈                     | callback 自己改 DOM 觸發自己 | [#29 self-mutation 處理](../mutation-observer-scope/)  |

本篇不展開設計細節（避免跟 #29 重複）、只談「audit 時怎麼識別這些 risk」。

---

## 跨 observer 類型的盤點

效能 audit 時、列出**所有** reactive 監聽器、不只 MutationObserver。各類型觸發來源不同、需要分別評估。

| 類型                                         | 觸發來源     | 過頻訊號                            |
| -------------------------------------------- | ------------ | ----------------------------------- |
| MutationObserver                             | DOM 變動     | 一次操作觸發 10+ 次                 |
| ResizeObserver                               | 元素尺寸變動 | 持續觸發（自激）/ resize 視窗時連發 |
| IntersectionObserver                         | 可視性變動   | scroll 時連發                       |
| Event listener (input / scroll / resize)     | 使用者互動   | 高頻事件未 debounce                 |
| `setInterval` / `requestAnimationFrame` 迴圈 | 時間         | 持續跑、不只在需要時                |

### 盤點工具

DevTools Performance 面板錄一段使用者操作、看 callback 觸發次數：

```js
// 在 callback 內加 console.count
new MutationObserver(function (mutations) {
  console.count('mutation observer fired');
  // ... 處理
}).observe(...);

new ResizeObserver(function (entries) {
  console.count('resize observer fired');
  // ... 處理
}).observe(...);
```

跑一次「使用者打字 + 等結果」的完整操作、看 console 各 listener 觸發幾次。

| 觸發次數         | 評估                         |
| ---------------- | ---------------------------- |
| 1-3 次           | 正常                         |
| 5-10 次          | 可能過頻、值得查             |
| 10+ 次           | 範圍 / option 太寬、需要收斂 |
| 持續觸發（不停） | 自激迴圈、需要立刻處理       |

---

## ResizeObserver 寫變數造成自激

ResizeObserver 的特殊風險是「寫 CSS 變數可能影響被觀察元素自己的尺寸」 — 這個 case 跟 [#29](../mutation-observer-scope/) 處理的 MutationObserver self-mutation 機制不同、值得獨立展開。

### 機制

```js
function syncScopeHeight() {
  document.documentElement.style.setProperty(
    '--search-scope-h', scopeEl.offsetHeight + 'px'
  );
}
new ResizeObserver(syncScopeHeight).observe(scopeEl);
```

如果 `--search-scope-h` 在 CSS 中被用來計算 `scopeEl` 自己的 padding / margin / height — 寫入觸發 layout、layout 觸發 resize、resize 觸發 callback、callback 又寫入。

### 症狀

- CPU 持續被佔
- Performance 面板看到 ResizeObserver callback 連發（>60/秒）
- 元素尺寸持續微調

### 解法

**結構分離**：寫的變數不該影響被觀察元素自己。

```js
new ResizeObserver(syncScopeHeight).observe(scopeEl);
// scopeEl 高度寫到 --search-scope-h
// CSS 中 --search-scope-h 用來計算 drawer 的 margin-top
// drawer 不是 scopeEl、不會反向觸發
```

設計時讓「觀察的元素」跟「受變數影響的元素」結構上分離 — 不會循環。

### 跟 MutationObserver self-mutation 的差異

| 觀察類型             | self-mutation 機制               | 處理                       |
| -------------------- | -------------------------------- | -------------------------- |
| MutationObserver     | callback 改 DOM 結構 / attribute | disconnect + observe 配對  |
| ResizeObserver       | callback 改變數 → 反向影響尺寸   | 結構分離（觀察 A、影響 B） |
| IntersectionObserver | callback 改可視性 → 反向觸發     | 罕見、設計時避免           |

ResizeObserver 沒有 disconnect 配對的等價技巧（disconnect 後再 observe 仍會立即重觸發） — 必須靠結構分離。

---

## 盤點的標準格式

每個 reactive 監聽器寫成一段註解、audit 時讀這份「設定卡」即可：

```js
/**
 * 監聽：.pagefind-ui 的子節點變動
 * 類型：MutationObserver
 * 範圍：subtree（深層也看）
 * Option：childList only
 * Callback 是否改 DOM：是（toggle class）
 * 自激風險：否（class change 不觸發 childList）
 * Debounce：80ms
 * 預期觸發頻率：使用者打字一次 < 5 次
 */
new MutationObserver(schedule).observe(ui, { childList: true, subtree: true });
```

audit 時、看註解就知道：

- 這個 observer 在做什麼
- 預期觸發頻率多少
- 實測超過預期 → 範圍太寬或 option 過勾

---

## 設計取捨：頻率管理策略選擇

當盤點發現某個 observer 觸發過頻、四種應對：

### A：縮 observer 範圍 / option（這個專案的預設）

- **機制**：subtree → 直接子；移除沒用的 option flag
- **選 A 的理由**：成本最低、改一行；觸發頻率倍數降低
- **適合**：絕大多數過頻 case
- **代價**：需要重新確認哪些變動類型真的需要監聽
- **詳細**：[#29 三維度收斂](../mutation-observer-scope/)

### B：加 debounce / throttle

- **機制**：高頻觸發合併成低頻 apply
- **跟 A 的取捨**：B 不解問題的根（觸發仍發生）、A 解根；但 B 對「無法縮範圍」的 case（如 input event）必要
- **B 比 A 好的情境**：使用者輸入事件、scroll 事件 — 本身高頻、無法縮範圍

### C：Disconnect / reconnect 配對

- **機制**：callback 改 DOM 前 disconnect、改完 reconnect
- **跟 A/B 的取捨**：C 處理 self-mutation、A/B 不處理；C 比 A/B 複雜
- **C 比 A/B 好的情境**：MutationObserver callback 必須改 DOM（沒有結構分離選項）
- **詳細**：[#29 self-mutation 處理](../mutation-observer-scope/)

### D：ResizeObserver 結構分離

- **機制**：觀察 A、影響 B（B ≠ A）
- **跟 C 的取捨**：ResizeObserver 沒 disconnect 等價技巧、必須用 D
- **D 是 ResizeObserver 自激的唯一解**

---

## 不該套用「頻率管理」的情境

不是所有 reactive 監聽器都需要管：

| 情境                                           | 為什麼可以放任       |
| ---------------------------------------------- | -------------------- |
| 開發階段、不上 production                      | 效能不影響真實使用者 |
| Callback 極輕（單次 < 0.1ms）                  | 觸發 100 次也才 10ms |
| 觸發頻率本來就極低（一次 setup 一次 callback） | 沒有頻率問題         |

**核心判準**：實測有效能問題嗎？沒有就不必預先優化。Audit 是「找已存在的問題」、不是「預防所有可能」。

---

## 跟其他原則的關係

| 篇                                                                 | 關係                                                                      |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| [#29 MutationObserver 範圍與觸發頻率](../mutation-observer-scope/) | 互補 — #29 是設計指引（怎麼寫 observer）、本篇是 audit 視角（怎麼找問題） |
| [#14 Selector 精準度](../dom-selector-precision/)                  | 跟 observer 範圍同源 — selector 起點就是 observer root 的選擇基礎         |
| [#34 Runtime 計算成本](../runtime-iteration-and-regex-cost/)       | 互補 — 本篇看「觸發次數」、#34 看「單次 callback 成本」                   |
| [#43 最小必要範圍](../minimum-necessary-scope-is-sanity-defense/)  | 「縮監聽範圍」是「最小必要範圍」原則的應用                                |

---

## 判讀徵兆

| 訊號                                    | 該檢查的位置                                                           |
| --------------------------------------- | ---------------------------------------------------------------------- |
| 使用者操作後瀏覽器卡頓                  | 該操作觸發了哪些 observer、各自觸發次數                                |
| CPU 持續 100%                           | observer 自激迴圈（特別是 ResizeObserver）                             |
| `setTimeout(0)` 也來不及處理            | observer / event 觸發頻率超過 schedule 處理速度                        |
| Callback 內加 console.count 數字爆炸    | observer 範圍過寬 — 收斂方式由 [#29](../mutation-observer-scope/) 處理 |
| ResizeObserver 在某 callback 後持續觸發 | 寫的變數反向影響觀察元素 — 結構分離                                    |

**核心原則**：reactive 監聽器的效能 audit = 列所有 listener + 量觸發次數 + 比對預期。發現問題後、設計修正方式由 [#29](../mutation-observer-scope/) 等設計指引篇展開 — 本篇只負責「找問題」這一步。
