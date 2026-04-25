---
title: "DOM 選擇與作用域的精準度"
date: 2026-04-25
weight: 14
description: "Selector 與 MutationObserver 的精準度直接決定『我要的元件被影響到、不該的不被影響到』。本文展開『最少必要範圍』的選擇原則。"
tags: ["report", "事後檢討", "JavaScript", "DOM", "工程方法論"]
---

## 核心原則

**Selector 涵蓋「最少必要範圍」、observer 監聽「最少必要事件」。** 寬泛的 selector / observer 換來「方便」、代價是難以預測的副作用 — 誤命中其他元素、頻繁觸發、在 layout 還沒穩時跑邏輯。從最具體開始、有需要再放寬。

---

## 為什麼精準度是 default

### 商業邏輯

DOM selector 與 MutationObserver 的範圍越寬、被誤命中或誤觸發的可能性越高。寬泛 selector 像「網撈」、可能撈到不在預期內的元素；寬範圍 observer 像「全頁監聽」、每個無關變動都觸發回呼、在 framework 連續 patch 時尤其浪費。

精準度的成本是「寫 selector / observer 時多想一點」、收益是「行為可預測、debug 範圍小」。

### 兩種精準度的失敗模式

| 失敗模式      | 表現                            | 根因                            |
| ------------- | ------------------------------- | ------------------------------- |
| Selector 過寬 | 該動的動了、不該動的也動了      | 沒指定 ancestor scope           |
| Observer 過寬 | 短時間內觸發數十次、layout 抖動 | 監聽 subtree 但只關心特定子節點 |

---

## 這次任務的具體應用

### 觀察 1：Scope filter 的 selector

第一次寫法：

```js
document.querySelectorAll('.pagefind-ui__result').forEach(...)
```

`document` 範圍 — 全頁面所有 `.pagefind-ui__result`。在搜尋頁這個 selector 沒問題（頁面只有一個 pagefind 實例）；但若未來同頁出現多個（例如「相關搜尋」widget），就會誤命中。

### 判讀

預設用 `document` 是「便利優先」、不是「精準優先」。改成從元件根節點往下查：

```js
var shell = document.querySelector('.search-shell');
shell.querySelectorAll('.pagefind-ui__result').forEach(...)
```

範圍縮到 `.search-shell` 內 — 即使未來頁面有第二個 pagefind 實例，scope filter 只影響我們管的那一個。

### 觀察 2：MutationObserver 的範圍

第一次寫法：

```js
new MutationObserver(apply).observe(ui, { childList: true, subtree: true });
```

監聽整個 `.pagefind-ui` 的 subtree childList 變動 — pagefind 重繪結果、加 / 移每個 result 元素都觸發 apply。一次搜尋觸發 10+ 次。

### 判讀 2

實際只關心「結果列表變動」。把 observer 範圍縮到 `.pagefind-ui__results`：

```js
var results = document.querySelector('.pagefind-ui__results');
new MutationObserver(apply).observe(results, { childList: true });
```

`childList: true`（不加 subtree）只監聽直接子節點增減 — pagefind 加 / 移 result 元素時觸發、改 result 內部不觸發。減少觸發次數、減少抖動。

### 執行原則

每個 selector / observer 都用三問檢查：

| 問題                                                 | 答案決定                  |
| ---------------------------------------------------- | ------------------------- |
| 我關心的元素只可能在哪些 ancestor 下？               | Selector 從哪個 root 開始 |
| 我關心的變動是哪一類（add / remove / attr / text）？ | Observer 開哪些 option    |
| 變動發生在哪一層（直接子 / 任意深度）？              | 是否要 subtree            |

---

## 內在屬性比較：四種 selector / observer 範圍

| 範圍                                                | 誤命中風險        | 觸發頻率        | 適用情境                 |
| --------------------------------------------------- | ----------------- | --------------- | ------------------------ |
| `document.querySelector`                            | 高 — 全頁面       | 不適用          | 不確定元素在哪、debug 時 |
| 元件根 `.querySelector`                             | 低 — 限縮在元件內 | 不適用          | 一般 selector 預設       |
| `observe(elem, { childList: true })`                | 不適用            | 低 — 只看直接子 | 直接子節點變動           |
| `observe(elem, { childList: true, subtree: true })` | 不適用            | 高 — 看整個子樹 | 確實需要看深層變動       |

優先選擇「最少必要範圍」 — 能用淺層的不用深層、能用元件根 query 的不用 document。

---

## Observer 的精準度技巧

### 1. 只看需要的變動類型

```js
// 只看子節點增減
{ childList: true }
// 只看屬性變化（特定屬性）
{ attributes: true, attributeFilter: ['data-state'] }
// 只看文字內容
{ characterData: true }
```

不要全部勾選 — 每個勾選都增加觸發頻率。

### 2. Debounce 防止抖動

```js
var timer;
function schedule() {
  clearTimeout(timer);
  timer = setTimeout(apply, 80);
}
new MutationObserver(schedule).observe(...);
```

Observer 觸發頻繁時、用 debounce 把多次觸發合併成一次 apply。

### 3. Disconnect 避免無限循環

```js
var observer = new MutationObserver(() => {
  observer.disconnect();   // 暫停監聽
  doSomething();           // 自己改 DOM 不會觸發 observer
  observer.observe(...);   // 恢復
});
```

當 apply 自己也改 DOM、會觸發 observer 再次執行 — 用 disconnect / observe 配對避免循環。

---

## Selector 的精準度技巧

### 1. 從元件根開始

```js
var shell = document.querySelector('.search-shell');
shell.querySelectorAll('.pagefind-ui__result');  // 限縮在 shell 內
```

不要直接 `document.querySelectorAll` — 把作用域限縮。

### 2. 用 attribute selector 縮範圍

```js
shell.querySelectorAll('.pagefind-ui__result[data-pagefind-rank]');
```

加 attribute filter 過濾掉初始化中的元素、只取已準備好的。

### 3. 排除已處理過的

```js
shell.querySelectorAll('.pagefind-ui__result:not([data-scoped])');
// ... 處理後加標記
el.setAttribute('data-scoped', 'true');
```

避免重複處理、減少 apply 內的工作量。

---

## 正確概念與常見替代方案的對照

### Selector 從具體走向放寬

**正確概念**：寫 selector 時從「最具體（元件根 + 特定 class + attribute）」開始，發現需要更多元素才放寬。

**替代方案的不足**：用 `document.querySelectorAll('.somethign')` 一網打盡 — 短期方便、長期容易誤命中。

### Observer 從淺層走向深層

**正確概念**：先用 `childList: true`（只看直接子）；確認不夠才加 `subtree: true`。

**替代方案的不足**：預設 `subtree: true` — 監聽範圍太大、framework patch 時觸發數十次、可能造成抖動。

### 變動類型逐一勾選

**正確概念**：根據實際關心的變動勾 observer option（childList / attributes / characterData）。

**替代方案的不足**：把所有 option 勾起來 — 「以防萬一」的代價是過度觸發、行為不可預測。

---

## 判讀徵兆

| 訊號                                    | 精準度問題                  | 修正動作                                     |
| --------------------------------------- | --------------------------- | -------------------------------------------- |
| Selector 命中了不該命中的元素           | Selector 太寬               | 加 ancestor scope，用 `parent.querySelector` |
| Observer 短時間觸發數十次               | Observer 範圍 / option 太寬 | 縮範圍 / 移除不需要的 option                 |
| Layout 在 framework patch 時抖動        | Apply 跑得太頻繁            | 加 debounce 把多次合併                       |
| Apply 內改 DOM 又觸發 observer 進入循環 | 沒處理 self-mutation        | 用 disconnect / observe 配對                 |

**核心原則**：精準度不是極致最佳化、是 sanity 防線。從具體開始、需要再放寬，比從寬泛開始一路追 bug 容易得多。
