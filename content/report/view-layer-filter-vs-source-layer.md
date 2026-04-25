---
title: "Filter 與 Source 的抽象層錯位"
date: 2026-04-26
weight: 55
description: "Filter 必須跟它過濾的資料源在同一層運作。視覺層的 filter 套在資料層分批產出的 source 上、會在「一筆」的定義上產生語意縫 — 使用者要的「全部符合」變成「目前載入的符合」、然後 silent 失敗。本文展開層錯位的識別與糾正。"
tags: ["report", "事後檢討", "工程方法論", "Architecture", "Data Flow"]
---

## 核心原則

**Filter 必須跟它過濾的資料源在同一層運作。** 把 filter 寫在視覺層（querySelector + show/hide）、把 source 留在資料層分批產出（paginated fetch / streaming / lazy iterator）— 兩層的「一筆」定義不一致、filter 看不到 source 還沒產出的東西、結果跟使用者意圖之間有語意縫。

更廣義的說法：**stream 操作（filter / sort / count / transform / search）必須跟 stream 的 materialization 同層或更上游**。在下游做 stream 操作、操作的對象是已經 materialize 的 subset、不是完整的 stream。

---

## 為什麼層錯位產生語意縫

### 「一筆」在不同層有不同定義

| 層     | 「一筆」是什麼           | 邊界                            |
| ------ | ------------------------ | ------------------------------- |
| 資料層 | Source 產出的一筆 record | 全部、或還沒產出的下一批        |
| 渲染層 | 已 render 進 DOM 的一筆  | = 已 fetch 並 render 過的子集   |
| 視覺層 | 螢幕上看得見的一筆       | = render 層之中沒被 hide 的子集 |

Filter 寫在視覺層、它的「過濾全部」≡「過濾螢幕上看得見的全部」≡「過濾已 fetch 已 render 的子集」。**離資料層的真實全集差兩層**。使用者意圖（「給我所有 title 含 X 的結果」）對應的是資料層的全集、不是視覺層的子集。

### Silent 失敗的條件

層錯位不會在「filter 子集裡有命中」的情境下被發現。它只在以下條件下顯露：

1. 已 materialize 的子集裡剛好沒命中
2. 但完整 stream 裡有命中、只是還沒 materialize
3. 使用者沒有訊號知道「還有沒抓的」

三個條件同時滿足、使用者看到「filter 後是空的」、誤以為是「沒有命中」、放棄。

### 為什麼這個 bug 容易寫出來

視覺層 filter 是寫起來最簡單的版本：

```js
items.forEach(el => {
  el.style.display = el.dataset.title.includes(query) ? '' : 'none';
});
```

5 行解決、看起來能用、第一輪測試（手動輸入 query → 看到 filter 生效）會通過。**「能用」的訊號出現太早、掩蓋了語意缺口**。

---

## 哪些 source 形狀有層錯位風險

| Source 型態                           | 是否有層錯位風險                |
| ------------------------------------- | ------------------------------- |
| 一次性 fetch、靜態陣列                | 否（沒有 subset）               |
| Paginated fetch（load more / cursor） | 是 — 本次任務的 case            |
| Streaming（SSE / WebSocket）          | 視 server 是否限額              |
| Lazy iterator + take(N) / break       | 是                              |
| Cached + revalidate                   | 是（cache vs fresh 兩 dataset） |

四類 source 共用同個結構：**source 分批 / 限額 / 延遲 materialize、filter 在下游 → silent 缺口**。詳細形狀分析見 [#63 資料源的形狀決定 feature 的形狀](../data-source-shape-defines-feature-shape/)。

---

## 這次任務的實際情境

### 觀察

搜尋頁實作 title / content filter：

```js
// pagefind 分批 load (load more 按鈕)
const results = await pagefind.search(query);
results.results.slice(start, start + 10).forEach(r => container.append(render(r)));

// 我們在 view 層 post-filter
function applyFilter(scope) {
  document.querySelectorAll('.result').forEach(el => {
    el.hidden = !matchesScope(el, scope);
  });
}
```

跑出來的問題：使用者選 title-only filter、第二批 8 筆全部 title 不含 query → 點 "load more" 後畫面閃了一下、新增的 8 筆全 hidden、使用者看到的內容沒變。

### 判讀

問題的根因不在「畫面閃」這個視覺現象、而在 filter 的層級錯位：

| 使用者意圖       | filter 實際對應           |
| ---------------- | ------------------------- |
| 「title 符合的」 | 「已載入 + title 符合的」 |
| 「全部結果」     | 「已載入的全部」          |

兩個定義在一般狀況看起來一樣（已載入子集裡有命中）、稀疏 case 暴露縫。

### 執行（解法選擇）

解法選擇展開見 [#59 Filter × Source 合成策略五選一](../filter-source-composition-strategies/) — A 推進 query / B 自動續抓 / C 預先 index / D 誠實 UX / E 明示縮小。本文聚焦「先識別這是層錯位、不是 UI bug」 — 識別錯了、後續解法都會在錯誤的層上補救。

---

## 內在屬性比較：filter 該放哪一層

| 層            | 看到的範圍       | 跟使用者意圖的距離 | 寫作成本           |
| ------------- | ---------------- | ------------------ | ------------------ |
| 視覺層        | 已 render 的子集 | 最遠（差兩層）     | 最低               |
| 渲染層        | 已 fetch 的子集  | 中（差一層）       | 低                 |
| 資料層 (源頭) | 完整 dataset     | 最近               | 中-高              |
| Source 之外   | 重 query         | 最近 + 最新        | 高（query 重設計） |

「寫作成本最低」跟「跟意圖最近」是反相關 — 這就是為什麼層錯位容易寫出來。

---

## 識別層錯位的三問

寫 filter / sort / count / transform 之前自問：

### 1. 這個操作的「對象」是什麼層的「一筆」？

如果寫在 view 層、對象是「螢幕上的元素」 — 那源頭如果分批、就有缺口。

### 2. Source 是「一次給完整 dataset」還是「分批 / 限額」？

對照前面「哪些 source 形狀有層錯位風險」表 — 任何分批 / 限額 / streaming / cached source 都有風險。一次性 fetch 或靜態陣列才安全。

### 3. 「沒命中」與「還沒 materialize」對使用者要不要區分？

要區分 → filter 必須在 source 層或自動續抓、否則使用者無法判斷。
不區分（可接受「在已載入範圍內找」這個語意） → view 層 filter 加誠實 UX。

三問跑完才寫 filter — 跳過任一問就可能掉進層錯位。

---

## 判讀徵兆

| 訊號                                                                                  | 該做的行動                                                                  |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 即將寫 `elements.forEach(el => el.hidden = !matches(el))`                             | 停 — 確認 source 是不是分批的；是 → 推到資料層                              |
| Source 是 `pagefind.search()` / `paginatedFetch()` / `for await` 但 filter 在 forEach | 是 — 重看「filter 該放哪一層」                                              |
| 不確定 source 真實 cardinality 跟分批機制                                             | 用 [#11 playwright](../playwright-early-in-loop/) 量 live source 的回傳數量 |
| Filter 後可能 0 筆但 source 還有未載入                                                | 必須補「自動續抓」或「誠實掃描範圍 UX」                                     |
| 「Load more」「Show next」按鈕存在、且有 filter                                       | 評估：filter 跟 load more 的 quota 是否同層                                 |
| 內心 OS：「先做出來、晚點補資料層」                                                   | 停 — 補不回來、會 ship 進 production silent 失敗                            |

**核心原則**：filter / sort / count / transform 是 stream operation、必須跟 stream 的 materialization 同層或更上游。寫在下游 = 操作 subset 而不是 stream、語意縫是必然、不是偶發 bug。
