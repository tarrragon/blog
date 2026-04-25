---
title: "在開發循環裡早一點用 playwright 看真實結果"
date: 2026-04-25
weight: 11
description: "靜態 CSS 推理跟視覺截圖溝通有極限 — 當行為與預期不符 ≥ 2 次，stop 推理、改用 playwright browser_evaluate 直接讀 live DOM。本文說明工具引入時機。"
tags: ["report", "事後檢討", "Playwright", "Debugging", "工程方法論"]
---

## 核心原則

**Playwright 不是最後手段、是縮短診斷迴圈的工具。** 當靜態 CSS 推理 + 視覺截圖溝通的循環失敗 ≥ 2 次、就應該停止推理、改用 playwright `browser_evaluate` 直接讀 live DOM 與 computed style。早一點用 = 試錯次數更少、心智負擔更輕。

---

## 為什麼推理迴圈有極限

### 商業邏輯

CSS 行為由「規則 + DOM tree + 樣式繼承 + 框架渲染」四個變數共同決定。靜態推理只能基於假設的 DOM tree — 假設錯了、推理就錯。視覺截圖溝通只能傳達「結果是什麼」、無法傳達「為什麼是這個結果」。

Playwright 的 `browser_evaluate` 直接執行 JS 在 live page、返回真實的 DOM tree、computed style、bounding rect — **把「四個變數」全部變成已知**。

### 推理 vs 量測的成本曲線

| 方法            | 第 1 次嘗試                 | 第 2 次             | 第 3 次以上             |
| --------------- | --------------------------- | ------------------- | ----------------------- |
| 靜態推理 + 截圖 | 快 — 假設正確時一次到位     | 慢 — 假設錯了得重來 | 越來越慢 — 假設錯誤累積 |
| Playwright 量測 | 中 — 起 server、寫 evaluate | 快 — server 已在跑  | 快 — 重用 setup         |

第 1 次推理快、後續成本爆炸；playwright 起步慢、後續穩定。**門檻在第 2 次**。

---

## 這次任務的實際情境

### 觀察

要把 search scope UI 放在「搜尋輸入框與結果之間」。

第一輪：基於 class name 推測 DOM tree、用 grid + display:contents 設 grid-row 排序。第二輪：發現 scope 跑到頁尾、嘗試調 grid-template-rows。第三輪：嘗試 absolute 定位但時機不對。第四輪：使用者說「思路錯了」、要我換方向。

### 判讀

四輪推理都基於同一個假設：`drawer` 是 `.pagefind-ui` 的直接子節點、跟 `form` 並列。實際用 playwright 一查：

```js
const drawer = document.querySelector('.pagefind-ui__drawer');
let parents = []; let el = drawer;
while (el && el !== document.body) {
  parents.push(el.tagName + '.' + el.className);
  el = el.parentElement;
}
```

返回：

```text
DIV.pagefind-ui__drawer
FORM.pagefind-ui__form    ← drawer 在 form 內！
DIV.pagefind-ui
```

假設錯了 — drawer 是 form 的 child、不是 sibling。grid 規則無論怎麼寫都不會生效，因為 drawer 跟 form 共用同一個 grid cell。

四輪推理 ≈ 30 分鐘。Playwright 一次查清楚 ≈ 2 分鐘。

### 執行

確認 DOM 結構後：grid 不適合這個場景、改用 absolute + drawer margin-top spacer。一次到位。

---

## Playwright 在開發循環的三個位置

### 1. 假設驗證

寫 CSS 規則前先量 DOM、確認結構符合假設。

```js
async () => ({
  parents: [].slice.call(document.querySelectorAll('.target')).map(el => {
    let chain = []; let n = el;
    while (n) { chain.push(n.tagName + '.' + n.className); n = n.parentElement; }
    return chain;
  })
})
```

### 2. 行為驗證

Layout 規則寫完後驗證實際結果。

```js
async () => ({
  rect: document.querySelector('.target').getBoundingClientRect(),
  computed: getComputedStyle(document.querySelector('.target')).gridRow,
})
```

### 3. 互動驗證

驗證使用者互動後的狀態。

```js
async () => {
  const input = document.querySelector('.search-input');
  input.value = 'pre';
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 1000));
  return Array.from(document.querySelectorAll('.result'))
    .filter(el => getComputedStyle(el).display !== 'none')
    .map(el => el.textContent.slice(0, 50));
}
```

---

## 內在屬性比較：四種 debug 方法

| 方法                          | 取得資訊量            | 重複成本           | 可寫成測試               |
| ----------------------------- | --------------------- | ------------------ | ------------------------ |
| 靜態 CSS 推理                 | 低 — 全是假設         | 高 — 每次重思考    | 否                       |
| 視覺截圖溝通                  | 中 — 只有結果         | 中 — 截圖 / 描述慢 | 否                       |
| 瀏覽器 DevTools               | 高 — DOM + computed   | 中 — 每次手點      | 否                       |
| Playwright `browser_evaluate` | 最高 — 程式化任意查詢 | 低 — 改 query 重跑 | 是 — 同樣 query 可寫測試 |

選擇順序：**簡單 layout 用 DevTools；複雜 / 反覆 debug 用 playwright；推理只在第 1 次試錯前**。

---

## 引入 playwright 的最低門檻

```bash
# 啟動本地 server（任何方式）
python3 -m http.server 8000 --directory public

# 或專案有 hugo
hugo server
```

Playwright MCP 提供：

- `browser_navigate(url)` — 開頁
- `browser_evaluate(fn)` — 執行 JS 拿結果
- `browser_take_screenshot()` — 截圖
- `browser_snapshot()` — accessibility tree

寫一個 evaluate fn ≈ 30 行 JS，比反覆推理快得多。

---

## 正確概念與常見替代方案的對照

### Playwright 是診斷工具、不是 last resort

**正確概念**：當推理 + 截圖循環的成本超過「起 server + 寫 evaluate」的成本，就切換到 playwright。門檻通常在第 2-3 次推理失敗。

**替代方案的不足**：把 playwright 當「最後手段」、堅持靠推理 — 推理錯誤累積、每輪都基於前輪錯誤假設、debug 時間爆炸。

### 量 live DOM 比讀 source 權威

**正確概念**：動態渲染的組件（svelte、react）source 看到的是 template、實際 DOM 可能多包了層。讀 live DOM。

**替代方案的不足**：只看 framework source 推結構 — runtime 行為可能加 wrapper、跟 source 不一致。

### Browser_evaluate 寫一段、查一片

**正確概念**：寫一個 evaluate fn 同時取得 DOM tree、computed style、bounding rect 多個資訊 — 一次量、整體判斷。

**替代方案的不足**：DevTools 一次查一個面板（Elements、Computed、Layout）— 切換面板慢、跨面板對照容易漏。

---

## 判讀徵兆

| 訊號                                | 工具切換時機    | 第一個該寫的 evaluate                |
| ----------------------------------- | --------------- | ------------------------------------ |
| 推理 ≥ 2 次失敗                     | 切到 playwright | 量目標元素的 ancestor chain          |
| Layout 在某些狀態下錯、其他狀態下對 | 切到 playwright | 量該元素在不同狀態下的 bounding rect |
| 改 CSS 不生效、specificity 看起來對 | 切到 playwright | 量 computed style 看真正套到的值     |
| 動態 DOM 結構不確定                 | 切到 playwright | 列出目標 container 的子節點          |

**核心原則**：縮短診斷迴圈的工具該早一點用、不該等到推理徹底失敗。第 2 次推理失敗就切換、別等第 5 次。
