---
title: "客製 UI 留 framework 邊界外、用 CSS 控制視覺位置"
date: 2026-04-25
weight: 5
description: "Svelte / React 等框架對自己管轄的 DOM 子樹有完整渲染週期 — 客製 UI 注入這個子樹會被框架重繪清掉。本文展開「邊界外 + CSS 視覺定位」這條策略：為什麼 framework 會清外來節點、CSS 怎麼達到注入想要的視覺效果、什麼時候這條策略不適用。"
tags: ["report", "事後檢討", "Svelte", "JavaScript", "CSS", "工程方法論"]
---

## 核心原則

**客製 UI 留在 framework 管轄的 DOM 邊界外、用 CSS（absolute、margin spacer、grid）達成想要的視覺位置。** 注入 framework 子樹的客製元素會被 reconciliation 清掉、跟渲染週期競爭、行為不可預測。邊界外的客製跟 framework 解耦、命運由我們自己決定。

> 本篇焦點：客製 UI 該放哪。**framework 元件本身需要動（搬節點、改順序、改 attribute）的安全規則**由 [#13 JS 操作 framework 元件：邊界辨識與安全規則](../component-boundary-and-js-impact/) 處理。

---

## 為什麼 framework 管轄區會清外來節點

### Reconciliation 機制

Svelte / React 等框架透過「component tree → DOM tree」的 reconciliation 機制保持 UI 與 state 同步。框架在 patch 時：

1. 比對 component tree 的當前狀態與目標狀態
2. 計算 DOM 需要的最小變動
3. 套用變動到實際 DOM

關鍵是步驟 2：**框架只認得自己 create 的節點**。外來節點（我們手動 appendChild 進去的）不在它的 component tree 裡、被視為「該節點不該存在」、清掉。

這不是 bug、是 reconciliation 的正常行為 — 框架要保證 DOM 跟 component state 一致、外來節點屬於不一致的部分。

### 外來節點的命運是不可預測的

不同框架 / 不同 reconciliation 策略對外來節點的處理：

| 框架           | 外來節點命運                    |
| -------------- | ------------------------------- |
| Svelte         | 多數情境清掉、視 patch 點而定   |
| React          | 通常清掉（Virtual DOM diff 時） |
| Vue            | 通常清掉、但 v-pre 包裹可保留   |
| Web Components | 由 component 內部邏輯決定       |

**「不可預測」本身就是問題** — 即使某次測試沒清、下次升級或 patch 時可能清。設計時不該依賴未明確保證的行為。

---

## 這次任務的具體情境

### 觀察

要把搜尋範圍切換 UI（scope radio group）放在「pagefind 搜尋輸入框與結果之間」 — 視覺上希望它就在 form 與 drawer 中間。

第一次嘗試：JS 把 scope element 用 `form.insertAdjacentElement('afterend', scopeEl)` 注入 `.pagefind-ui` 內部。

結果：使用者打字後 scope 消失。

### 判讀

Pagefind 用 svelte 構建 UI、reactivity 監聽 search query 變動。Query 改變時 svelte 會 patch `.pagefind-ui` 的子樹 — 我們注入的 scope 不是 svelte 認得的節點、被視為差異清掉。

### 執行：邊界外 + CSS 控制位置

策略改為「scope 留在 `.search-shell` 裡（framework 邊界外）、用 CSS absolute 浮在 form 上」：

```html
<div class="search-shell">
  <h1>...</h1>
  <div class="search-scope">...</div>      <!-- 邊界外、永不被清 -->
  <div id="search">...</div>               <!-- pagefind 進來這裡 -->
</div>
```

```css
.search-shell { position: relative; }
.search-scope {
  position: absolute;
  top: calc(var(--search-title-h) + var(--search-form-h) + 4px);
  /* ... */
}
.search-shell .pagefind-ui__drawer {
  margin-top: calc(var(--search-scope-h) + 8px);  /* 為 scope 讓位 */
}
```

scope 不在 svelte 管轄區、永遠不被清；視覺位置靠 absolute + drawer 的 margin-top 共同決定。

---

## CSS 達成視覺位置的設計工具

### 工具 1：Absolute + 容器 relative

把客製 UI 設 `position: absolute`、容器設 `position: relative` 當定位基準。

```css
.search-shell { position: relative; }
.search-custom { position: absolute; top: ...; left: ...; }
```

客製 UI 跟 framework 元素脫離 layout flow、各自獨立。

### 工具 2：Margin spacer 推開 framework 元素

要在 framework 元素之間插入空間放客製 UI、改 framework 元素的 margin / padding 推出空間：

```css
.framework-element { margin-top: var(--custom-height); }
.custom-ui { position: absolute; top: 0; height: var(--custom-height); }
```

framework 元素留出空間、客製 UI 浮在空間上。

### 工具 3：Grid 容器讓 framework 元件當 grid item

```css
.search-shell {
  display: grid;
  grid-template-rows: auto auto 1fr;
}
.search-shell > .search-scope { grid-row: 2; }
.search-shell > #search { grid-row: 3; }
```

把 framework 元件當 grid 的一個 item — grid 控制 layout、framework 不知道有 grid 在外層、繼續管它的子樹。

### 工具 4：用 CSS variables 共享尺寸

framework 元素的尺寸需要參考客製 UI 時、用 CSS variable 傳遞：

```css
:root { --custom-height: 60px; }
.framework-element { margin-top: var(--custom-height); }
.custom-ui { height: var(--custom-height); }
```

或用 ResizeObserver 量測寫回 variable（[#27 runtime 量測模式統一](../runtime-measurement-unification/)）。

---

## 設計取捨：客製 UI 的位置選擇

四種做法、各自機會成本不同。這個專案選 A（邊界外 + CSS）當預設、其他做法在特定情境合理。

### A：framework 邊界外 + CSS 視覺定位（這個專案的預設）

- **機制**：客製 UI 放在 framework 元件的 sibling 位置、用 CSS absolute / grid / margin spacer 達成視覺位置
- **選 A 的理由**：跟 framework reconciliation 完全解耦、命運由自己決定、升級不影響
- **適合**：絕大多數需要在 framework UI 旁 / 上 / 下加客製內容的情境
- **代價**：CSS 定位邏輯比 DOM 巢狀複雜、需要正確處理 stacking context / z-index

### B：framework 邊界外 + JS 量測位置

- **機制**：用 ResizeObserver 量 framework 元素的 bounding rect、JS 算出客製 UI 該擺哪
- **跟 A 的取捨**：A 用 CSS 表達靜態關係、B 處理 runtime 才知道的尺寸；B 多一層 JS、但能達成 CSS 表達不出的精確定位
- **B 比 A 好的情境**：客製 UI 位置依賴 framework 元件的 runtime 尺寸（內容換行、字型變化）

### C：framework 邊界內注入

- **機制**：JS 把客製 element 直接 appendChild 到 framework 子樹內
- **跟 A 的取捨**：C 看似省事（少一層 wrapper）、實際把客製命運綁在 framework reconciliation 上
- **C 才合理的情境**：該 framework 子樹確認「不會被 reconcile」（極罕見、需要讀框架 source 確認）
- **代價**：客製可能在任何 patch 時消失、需要 MutationObserver 補打、跟渲染週期賽跑

### D：Fork framework source

- **機制**：fork 整個 framework、改 reconciliation 行為讓它認得我們的客製
- **成本特別高的原因**：每次升級都要重新 merge、客製永久綁在 fork 版本
- **D 才合理的情境**：framework 已停止維護、且客製需求超過所有其他選項

---

## 不該套用「邊界外」的情境

A 是預設、但不是萬靈丹：

| 情境                                                              | 為什麼不適合 A                               |
| ----------------------------------------------------------------- | -------------------------------------------- |
| 客製內容必須在 framework 元件的內部視覺脈絡內（共享 inline flow） | Absolute 跳出 flow、達不到 inline 的視覺效果 |
| Framework 元件本身就是要客製化（改 row、改 cell）                 | 動的是 framework 本身、不是「在旁邊加東西」  |
| Framework 提供了官方擴展介面（slot、render prop）                 | 用官方介面更穩、不需要邊界外 hack            |
| 客製需要訪問 framework 的內部 state                               | 邊界外的客製跟內部 state 隔離、訪問成本高    |

**核心判準**：客製是「在 framework 旁邊加東西」還是「改 framework 本身」？前者用本策略、後者另想辦法。

---

## 跟其他原則的關係

| 抽象層原則                                                                             | 關係                                                                                                |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| [#45 跟外部組件合作的層次](../external-component-collaboration-layers/)                | 「邊界外 + CSS」是「不要挖 framework 內部」的具體應用 — 客製貼著外部介面（DOM sibling）做、不挖內部 |
| [#42 2 次門檻](../two-occurrence-threshold/)                                           | 第 1 次注入失敗（被清掉）= 第 2 次該換策略到邊界外、不該繼續嘗試「換種方式注入」                    |
| [#13 JS 操作 framework 元件：邊界辨識與安全規則](../component-boundary-and-js-impact/) | 互補關係 — 本篇處理「客製 UI 該放哪」、#13 處理「framework 元件本身要動時怎麼動」                   |

---

## 判讀徵兆

| 訊號                                            | 該怎麼處理                                                      |
| ----------------------------------------------- | --------------------------------------------------------------- |
| 注入 framework DOM 的元素在使用者互動後消失     | 把該元素搬出 framework 邊界、用 CSS 控制視覺位置                |
| 客製 UI 在 framework 更新後 attribute 被 revert | 客製 UI 不該在 framework 內、wrapper 在外、attribute 套 wrapper |
| 看不出哪些 DOM 是 framework 管的                | 讀 framework 的 mount root、從那裡往內都是管轄區                |
| Stacking context 衝突、z-index 失靈             | 確認 absolute 的 containing block 是預期的 relative parent      |
| Framework 元件位置不固定、客製 UI 對不齊        | 用 ResizeObserver 量 framework 元素、寫回 CSS variable          |

**核心原則**：客製 UI 的存活壽命 = 「離 framework 管轄區多遠」。最遠 = 永遠不被清；注入內部 = 隨時可能消失。預設選邊界外、不要為了「省一層 wrapper」進入 framework 領地。
