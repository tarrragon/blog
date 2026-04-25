---
title: "排版精度的工具選擇：CSS-only vs JS-assisted"
date: 2026-04-25
weight: 12
description: "CSS 適合 build-time 可決定的 layout、JS 適合 runtime 才知道的尺寸與 DOM 移動。混淆兩者會讓 layout 跟 framework 渲染週期競爭。本文展開選擇規則。"
tags: ["report", "事後檢討", "CSS", "JavaScript", "工程方法論"]
---

## 核心原則

**CSS 處理 build-time 可決定的 layout、JS 處理 runtime 才知道的尺寸與 stateful DOM 移動。** 邊界誤判：硬要 CSS 解決 runtime 問題會反覆試錯；硬要 JS 解決 layout 問題會跟 framework 渲染競爭。

選擇問題簡化為兩問：

1. 這個值在 build time 能定下來嗎？能 → CSS；不能 → JS 量測寫回 CSS 變數。
2. 這個 DOM 變動是 framework 管的嗎？是 → 不要動；不是 → JS 可動。

---

## 為什麼分工是必要的

### 商業邏輯

CSS 的設計假設是「規則在 build time 決定、瀏覽器渲染時應用」。CSS 沒有 reactive 機制 — 沒辦法「等元素渲染完才知道高度然後對齊」。

JS 的設計假設是「runtime 可以讀寫 DOM 與 style」。JS 可以在元件渲染後量測尺寸、可以隨 viewport 變動 reparent 節點。

**用錯工具不只「不太優雅」、是直接做不到**。要 CSS 解決動態尺寸只能寫 magic number（猜的）；要 JS 解決靜態 layout 寫了一堆 imperative 代碼還可能跟 framework 衝突。

---

## 這次任務的工具分配

### CSS 處理的部分

| 任務                            | CSS 寫法                                        | 為什麼用 CSS                  |
| ------------------------------- | ----------------------------------------------- | ----------------------------- |
| H1 / search input 的固定高度    | `height: 64px` 寫死                             | Build time 可決定的設計 token |
| 搜尋頁主欄置中、breakpoint 切換 | `@media (min-width: 1400px)`                    | 純宣告式 layout               |
| Filter sidebar absolute 定位    | `position: absolute; right: calc(100% + 2rem)`  | 靜態定位關係                  |
| Drawer 留出 scope 空間          | `margin-top: calc(var(--search-scope-h) + 8px)` | 引用變數的 calc               |

### JS 處理的部分

| 任務                                  | JS 寫法                                      | 為什麼用 JS                       |
| ------------------------------------- | -------------------------------------------- | --------------------------------- |
| 量測 scope 高度寫回 CSS 變數          | ResizeObserver                               | Runtime 才知道（字型、換行）      |
| Filter sidebar 切換到 mobile drawer   | matchMedia + appendChild                     | 跨 viewport 的 stateful DOM 移動  |
| Scope filter（regex 比對標題 / 內文） | event listener + setProperty                 | 純 runtime 邏輯、無 build time 解 |
| Scope UI 寫死值與量測值的橋           | `style.setProperty('--search-scope-h', ...)` | JS 寫回讓 CSS 用                  |

---

## 兩問判斷法

### 問 1：這個值在 build time 能定下來嗎

| 值                                       | Build time 知道嗎 | 工具                     |
| ---------------------------------------- | ----------------- | ------------------------ |
| 設計 token（spacing、typography scale）  | 是                | CSS 變數寫死             |
| 元件固定尺寸（icon size、button height） | 是                | CSS height / width       |
| 響應式 breakpoint                        | 是（設計決定）    | `@media` query           |
| 動態文字塊高度（受字型 / 換行）          | 否                | JS ResizeObserver        |
| 元件位置（隨 viewport 變化）             | 否                | JS getBoundingClientRect |

知道 → CSS 解。不知道 → JS 量測寫回 CSS 變數、CSS 從變數計算。

### 問 2：這個 DOM 變動是 framework 管的嗎

| 變動                            | Framework 管      | 工具       |
| ------------------------------- | ----------------- | ---------- |
| 自家 DOM 內元素加 / 移 / 改     | 否                | JS 自由動  |
| Framework 元素的整節點 reparent | 不管內部          | JS 可搬    |
| Framework 元素內部的子節點      | 是                | 不要動     |
| Framework 元素的 attribute      | 視 framework 而定 | 通常不要動 |

是 → 不要動，用 CSS 視覺解。不是 → JS 可動。

---

## 內在屬性比較：兩種工具的特性

| 屬性               | CSS-only                     | JS-assisted                     |
| ------------------ | ---------------------------- | ------------------------------- |
| 知識成本           | 低（語言簡單）               | 中（需要 DOM API）              |
| 執行時機           | 渲染前 / 樣式重新計算        | DOMContentLoaded 後 / 事件觸發  |
| 是否阻塞首次渲染   | 是（CSS 是 render-blocking） | 否（async）                     |
| Framework 衝突風險 | 無                           | 有（若動到 framework 管的 DOM） |
| 可維護性           | 高（純 declarative）         | 中（imperative）                |
| 跨瀏覽器一致性     | 高（CSS 標準清楚）           | 中（API 差異）                  |

優先 CSS — declarative、無 framework 衝突、首次渲染就生效。JS 補 CSS 做不到的部分。

---

## 邊界誤判的兩種失敗

### CSS 解 runtime 問題

例：用 CSS magic number 寫死 scope-h（猜 56px），實際渲染 73.5px、對齊壞掉。

修法：認知到「scope-h 是 runtime 才能知道的值」、改用 ResizeObserver 量測寫回 CSS 變數。

### JS 解 framework-managed layout

例：用 JS `appendChild` 把 scope UI 注入 `.pagefind-ui` 內、Svelte 重繪時清掉。

修法：認知到「`.pagefind-ui` 是 framework 邊界內」、改用 CSS absolute 把 scope 浮在外部。

---

## 設計取捨：CSS / JS 工具分配策略

四種做法、各自機會成本不同。這個專案以 A（CSS-first、JS 透過變數補）為主、其他做法在特定情境合理。

### A：CSS-first、JS 透過 CSS 變數補 runtime 值（這個專案的預設）

- **機制**：CSS 處理 build time 可決定的 layout、JS 量測 runtime 值寫回 CSS 變數、CSS 從變數計算
- **選 A 的理由**：CSS 是 declarative 不阻塞首次渲染、跟 framework 不衝突；變數是 JS-CSS 介面、單向資料流
- **適合**：絕大多數客製情境
- **代價**：需要明確分辨「值能在 build time 定下來嗎」、JS 寫法要是「寫回變數」而不是「直接改 inline style」

### B：純 CSS-only（無 JS）

- **機制**：純宣告式、不寫 JS
- **跟 A 的取捨**：B 完全無 JS 維護成本、A 多一層 JS；但 B 對 runtime 才知道的尺寸（內容動態）束手無策
- **B 比 A 好的情境**：所有值都能 build time 確定、layout 完全靜態

### C：JS-imperative layout（每次重算）

- **機制**：JS 監聽變動、每次重新計算所有元素位置、寫 inline style
- **成本特別高的原因**：imperative 代碼難維護、首次渲染慢（要等 JS 跑）、跟 framework 渲染衝突
- **C 才合理的情境**：CSS 表達不出的複雜 layout（極罕見、現代 CSS 已涵蓋大多數）

### D：CSS magic number 估算 runtime 值

- **機制**：CSS 內寫死「應該差不多」的值（不量測）
- **跟 A 的取捨**：D 看似省 JS、實際對齊在邊界情境（字型 / theme）必壞
- **D 才合理的情境**：實務上幾乎不存在 — 「runtime 才知道的值」用 CSS 估算是錯誤工具選擇

---

## 判讀徵兆

| 訊號                                         | 工具誤用方向                 | 修正動作                                 |
| -------------------------------------------- | ---------------------------- | ---------------------------------------- |
| CSS 寫了 magic number、改字型後對不齊        | 用 CSS 解 runtime 問題       | 量測該值、改 ResizeObserver 寫回變數     |
| JS 寫了 100+ 行做 layout                     | 用 JS 解靜態 layout 問題     | 退回 CSS、用 grid / flex / absolute 達成 |
| JS 改 framework DOM 後，framework 更新就失效 | JS 動到 framework 管的領域   | 改用 CSS 視覺定位、不動 framework DOM    |
| Inline style 散落多處難 debug                | JS 直接寫 style 而非透過變數 | 重構成「JS 寫 CSS 變數、CSS 從變數計算」 |

**核心原則**：選工具不是品味問題、是「值能不能在 build time 定下來」「DOM 是不是我管」兩個技術問題的答案。問清楚再選。
