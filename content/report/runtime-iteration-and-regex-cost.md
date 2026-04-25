---
title: "Runtime 計算成本：每筆迭代與正則"
date: 2026-04-25
weight: 34
description: "Scope filter 對每筆結果跑 regex — 結果數量大時成為 frame budget 的主要消耗。本文盤點此類「每筆迭代 + per-item 計算」的風險點與評估方法。"
tags: ["report", "事後檢討", "Performance", "JavaScript", "工程方法論"]
---

## 核心原則

**每筆迭代的成本 = 單次計算 × 迭代次數。** 兩個變數都會放大效能問題；單次計算便宜時、迭代次數變多仍可能爆掉 frame budget。盤點時兩維度一起看、不只看單筆。

---

## 為什麼迭代次數值得獨立看待

### 商業邏輯

開發階段測試的資料量通常少（10 筆結果）— 單次迭代 + 10 次 = 不痛。

上線後資料量放大（200 筆結果）— 同樣的單次計算 × 200 = 痛。

**單次計算的最佳化收益是固定倍數、迭代次數的成長是線性放大** — 後者更值得關注。

### 三類迭代成本

| 類型            | 例                                     |
| --------------- | -------------------------------------- |
| 對 DOM 集合迭代 | `forEach` over `querySelectorAll` 結果 |
| 對資料陣列迭代  | `map` / `filter` over 大量物件         |
| 對 DOM 樹遞迴   | `.contains()` 或 ancestor walk         |

每類有不同的優化策略、共通是「先量規模再決定動哪」。

---

## 搜尋頁的具體風險點

### 風險 1：scope filter 對每筆 result 跑 regex

**位置**：`assets/search.js` 的 `apply()`。

```js
items.forEach(function (el) {
  var titleEl   = el.querySelector('.pagefind-ui__result-title');
  var excerptEl = el.querySelector('.pagefind-ui__result-excerpt');
  var title   = titleEl   ? titleEl.textContent   : '';
  var excerpt = excerptEl ? excerptEl.textContent : '';
  var show = scope === 'title' ? re.test(title) : re.test(excerpt);
  // ...
});
```

每筆 result 做的事：

1. 兩次 `querySelector`（DOM 查詢）
2. 兩次 `textContent` 讀取（DOM 屬性讀取）
3. 一次 `re.test`（正則比對）
4. 一次 `classList.toggle`（class 操作）

單筆 ~0.1ms 等級、看 DOM 大小。

**判讀**：

- 結果 10 筆 → 1ms、無感
- 結果 100 筆 → 10ms、接近 frame budget（16.67ms）
- 結果 500 筆 → 50ms、明顯卡頓

**症狀**：使用者打字時 input lag、scroll jank。

**第一個該查的**：DevTools Performance 面板錄一次 apply、看 forEach 那段佔多少。> 5ms 開始考慮優化。

### 風險 2：textContent 讀取的隱藏成本

**位置**：上述 `titleEl.textContent`。

**判讀**：`textContent` 看似簡單、實際在某些瀏覽器中要 traverse 整個子樹拼字串。對於有 highlight `<mark>` 標籤的結果、textContent 要組合多個 text node。

**症狀**：textContent 比預期慢、特別在 result 內結構複雜時。

**第一個該查的**：用 `console.time` 量一次 textContent 讀取、看單次幾 ms。

### 風險 3：每次 apply 都重新 querySelector

**位置**：`apply()` 每次跑都 `document.querySelectorAll('.pagefind-ui__result')`。

**判讀**：querySelector 是 fresh 查詢、不快取。每次 apply 都重新掃 DOM 找到結果集合。

**症狀**：apply 觸發頻繁時、querySelector 是固定開銷。

**第一個該查的**：把結果集合 cache 一份、observer 觸發時更新 cache、apply 用 cache 不重查 DOM。

### 風險 4：Regex 編譯成本

**位置**：

```js
var re = new RegExp(escapeRegex(query), 'i');
```

每次 apply 編譯一次 regex。

**判讀**：Regex 編譯成本比想像中重 — 對複雜 pattern 可達數 ms。

**症狀**：query 字串長、apply 觸發頻繁時、regex 編譯佔 frame budget。

**第一個該查的**：把 regex cache 起來、query 變動才重編譯。

---

## 內在屬性比較：四種優化方向

| 方向                                            | 縮減幅度           | 複雜度 | 適用情境                     |
| ----------------------------------------------- | ------------------ | ------ | ---------------------------- |
| 縮迭代次數（IntersectionObserver 只處理可視區） | 大                 | 中     | 結果數量大、多數不在可視範圍 |
| 縮單次計算（cache textContent / regex）         | 中                 | 低     | 重複計算同樣的東西           |
| 分批處理（requestIdleCallback / chunk）         | 大 — 攤開時間      | 中     | 一次處理量大但可延後         |
| Web Worker                                      | 最大 — 獨立 thread | 高     | 純計算密集、跟 DOM 無關      |

對 scope filter 的場景：**IntersectionObserver 只處理可視區** + **regex cache** 是性價比最高的兩項。

---

## 規模放大的盤點

對每個迭代的 callback、預先估算「規模放大時會怎樣」：

| 當前規模                   | 10x 規模                        | 100x 規模                 |
| -------------------------- | ------------------------------- | ------------------------- |
| 10 筆 result × 0.1ms = 1ms | 100 筆 = 10ms（接近 16ms 上限） | 1000 筆 = 100ms（明顯卡） |

10x / 100x 的數字是「未來內容增長 1 個 / 2 個數量級」的預警。當前 fine 但 10x 後不 fine、值得提前考慮優化機制。

---

## 設計取捨：per-item 迭代成本的優化策略

四種做法、各自機會成本不同。預設先做 A（縮迭代次數）、A 不夠才考慮 B/C/D。

### A：縮迭代次數（IntersectionObserver / 分頁 / 過濾）（這個專案的預設）

- **機制**：用 IntersectionObserver 只處理可視區、用過濾條件預先排除大量項目
- **選 A 的理由**：縮減幅度大（線性放大反向操作）、callback 內部不變
- **適合**：結果數量大、但實際需要處理的部分少（多數在可視區外）
- **代價**：增加 observer setup、需要設計「該處理什麼項目」的判斷

### B：縮單次計算（cache textContent / regex / DOM query）

- **機制**：把重複計算的結果 cache、避免每次重做
- **跟 A 的取捨**：B 縮減幅度中等（看 cache 命中率）、A 縮減幅度大；兩者解不同問題、可並用
- **B 比 A 好的情境**：迭代次數無法縮（必須處理所有項目）、但每項計算重複（regex 編譯、textContent 重讀）

### C：分批處理（requestIdleCallback / chunk）

- **機制**：把一次處理拆成多次、攤開到多個 frame
- **跟 A/B 的取捨**：C 攤開時間、A/B 縮減總時間；C 在「總時間無法縮、但可以延後」時合理
- **C 比 A 好的情境**：處理量大但可延後（initial render 時的非關鍵 enhancement）

### D：Web Worker

- **機制**：把計算搬到獨立 thread
- **跟 A/B/C 的取捨**：D 完全不阻 main thread、但 setup 成本高（postMessage 序列化）
- **D 才合理的情境**：純計算密集、跟 DOM 無關（搜尋 indexing、複雜資料處理）— 對 DOM 操作沒意義（Web Worker 不能直接動 DOM）

---

## 判讀徵兆

| 訊號                                 | 該檢查的位置                             |
| ------------------------------------ | ---------------------------------------- |
| forEach over 大集合佔用 frame budget | 用 IntersectionObserver 只處理可視區     |
| 每次 apply 重做相同的查詢 / 編譯     | Cache 結果、變動觸發時更新 cache         |
| Async 處理可接受時還在同步跑         | 改 requestIdleCallback / 分批 setTimeout |
| 資料量比測試時大 N 倍後才發現問題    | 開發時做規模 10x / 100x 預估             |

**核心原則**：「每筆都做」的計算成本 = 每筆 × 筆數。優化時兩維度都看、不要只盯單次。
