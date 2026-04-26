---
title: "Layout reflow / repaint 的可量化評估"
date: 2026-04-25
weight: 35
description: "Filter slot 切換、CSS 變數寫入、絕對定位重算 — 哪些操作觸發 reflow 而非僅 repaint、用什麼工具量、評估值落在哪個區間值得優化。"
tags: ["report", "事後檢討", "Performance", "CSS", "工程方法論"]
---

## 核心原則

**Reflow 與 repaint 的成本差兩個數量級、用 Performance 面板可以量化判斷哪個發生。** 開發時不需要「全部避開 reflow」、要做的是「知道哪些操作觸發 reflow、規模放大時哪些值得優化」。

---

## 為什麼要量化、不憑感覺

### 商業邏輯

瀏覽器渲染管線分階段：

| 階段            | 觸發條件                            | 相對成本                   |
| --------------- | ----------------------------------- | -------------------------- |
| Style recalc    | CSS 規則變動、class toggle          | 低                         |
| Layout (reflow) | 影響元素尺寸 / 位置的 CSS 改變      | 高（要重算所有受影響元素） |
| Paint (repaint) | 顏色 / 背景變動但位置不變           | 中                         |
| Composite       | transform / opacity 等 GPU 加速屬性 | 最低                       |

不同操作落在不同階段。「改 width」觸發 reflow、「改 transform」只到 composite。差距 ~10-100x。

但這不代表要「永遠用 transform」 — 多數場景 reflow 成本可以接受、過度避免反而讓 layout 變脆。

### 量化的工具

| 工具                                     | 看什麼                                     |
| ---------------------------------------- | ------------------------------------------ |
| Chrome DevTools Performance              | 整段操作的 reflow / paint / composite 時間 |
| Performance API（`performance.measure`） | 程式化量自家函式                           |
| Layout shift (Web Vitals CLS)            | 視覺上的 layout 跳動                       |

優先用 DevTools Performance 量、有具體數字後再決定是否優化。

---

## 搜尋頁的具體風險點

### 風險 1：Filter slot 跨 viewport 切換

**位置**：matchMedia callback 內 `slot.appendChild(filter)` / `drawer.insertBefore(filter, ...)`。

**判讀**：

- 整個 filter 子樹移動 = layout 重算（filter 的新位置、原位置元素重排）
- 同時 main 區域與 sidebar 區域的尺寸都重算
- 一次性發生、不持續觸發

**症狀**：使用者拖動視窗寬度跨過 1400px 時、瞬間卡頓 1-2 frame。

**第一個該查的**：DevTools Performance 錄下 resize 跨過 breakpoint 的瞬間、看 Layout 區塊有多大。< 16ms = OK；> 16ms 考慮 debounce matchMedia callback。

### 風險 2：CSS 變數寫入

**位置**：`document.body.style.setProperty('--search-scope-h', ...)`。

**判讀**：寫 CSS 變數不一定觸發 reflow — 看哪些規則用了這個變數、那些規則影響哪些元素。

- `--search-scope-h` 用於 drawer 的 `margin-top` → drawer 位置變動 → reflow
- `--search-scope-h` 用於 filter slot 的 `padding-top` → filter slot 高度變動 → reflow

**症狀**：scope 大小變動時、drawer 與 filter slot 同時重排、可能看到輕微跳動。

**第一個該查的**：DevTools Performance 錄一次 scope 變大的事件、看 Layout 區塊。多數場景 < 5ms、可忽略。

### 風險 3：Absolute 定位的重算

**位置**：`.search-filter-slot { position: absolute; ... }`。

**判讀**：Absolute 元素跟一般 flow 元素分離、自己不影響 sibling 的 layout、但仍受自身 position / size 變動影響。Filter 改 top 觸發自身 reflow、不影響 main。

**症狀**：filter slot 的 padding-top 變動（隨 scope-h）— 只影響 filter 自身高度。

**第一個該查的**：DevTools Performance 看 filter padding 變動時的 layout 範圍 — 應該只到 filter 內部、不擴散到 main / footer。若擴散表示有意外的 stacking context 影響。

### 風險 4：JS 連續操作 DOM

**位置**：`reorderFilters()` 用 `appendChild` 多次調整順序。

```js
desiredOrder.forEach(function (k) {
  if (byKey[k]) filter.appendChild(byKey[k]);
});
```

**判讀**：

- 多次 `appendChild` 可能觸發多次 layout
- 但 browser 通常會合併同步 DOM 變動到一次 layout（natural batching）
- 真正會「強制 layout」的是 DOM 寫入後馬上讀 layout 屬性（如 offsetHeight）

**症狀**：rare — reorder 一次只在 setup 時跑、影響很短。

**第一個該查的**：若有這類「寫後立刻讀」的 pattern、用 `requestAnimationFrame` 把讀延後到下一幀、避免 forced sync layout。

---

## 內在屬性比較：四種 layout 變動類型

| 變動類型                              | 成本  | 可控性                 |
| ------------------------------------- | ----- | ---------------------- |
| Composite-only（transform / opacity） | 最低  | GPU 加速、< 1ms        |
| Paint-only（顏色變動）                | 低    | 局部重繪               |
| Layout（尺寸 / 位置變動）             | 中-高 | 要算受影響的範圍       |
| Forced sync layout（DOM 寫後立刻讀）  | 最高  | 連續觸發是 perf killer |

選擇順序：**有意識避免 forced sync layout**、**對動畫優先用 transform**、**一般 layout 變動量小不必特別避免**。

---

## 預估成本的快速法則

不要每個操作都用 DevTools 量、用快速法則先判斷：

| 操作                      | 預估等級 | 何時要量                        |
| ------------------------- | -------- | ------------------------------- |
| 改 class（class toggle）  | 1ms 等級 | 套用到大量元素時                |
| Append / remove 單一節點  | 1-5ms    | 大規模迭代時                    |
| 移動 DOM 子樹（reparent） | 5-20ms   | 子樹大、頻繁觸發時              |
| 改 CSS 變數（簡單 calc）  | 1-5ms    | 頻繁觸發時                      |
| Forced sync layout        | 5-50ms   | 任何寫後立刻讀的 pattern 都該量 |

預估超過 frame budget（16.67ms）才值得實際量、進一步優化。

---

## 設計取捨：layout 操作的處理策略

四種做法、各自機會成本不同。這個專案選 A（量化評估再決定）當預設、其他做法在特定情境合理。

### A：量化評估、按規模決定優化與否（這個專案的預設）

- **機制**：用 DevTools Performance 量每個 layout 操作的實際成本、超過 frame budget（16.67ms）才優化
- **選 A 的理由**：避免過度優化（多數 reflow 成本可接受）、又不漏真正貴的（forced sync layout）
- **適合**：所有效能盤點情境
- **代價**：需要學會用 DevTools Performance、對效能 dispute 要量

### B：全部用 transform / opacity 避免 reflow

- **機制**：所有動畫 / 變動都用 transform 或 opacity（GPU composite）
- **跟 A 的取捨**：B 預先避免 reflow、A 量化按需處理；但 B 寫出複雜的 transform / absolute 組合、layout 邏輯難維護
- **B 比 A 好的情境**：高頻動畫（每 frame 變動的旋轉 / 移動）— 確定觸發 layout 會卡

### C：完全避免 layout 操作

- **機制**：把所有可能觸發 reflow 的操作都繞開
- **跟 A/B 的取捨**：C 過度反應、A/B 適度；C 寫法極受限、layout 表達力下降
- **C 才合理的情境**：純動畫場景（沒有 layout 需求）— 對一般 UI 不適用

### D：不量、靠經驗判斷

- **機制**：依「我覺得這應該快」做決定
- **成本特別高的原因**：瀏覽器 / 設備 / 場景差異大、直覺不可靠；可能漏掉 forced sync layout 等真正貴的 pattern
- **D 是反模式**：效能 dispute 必須有數字 — 直覺判斷會漏掉 forced sync layout 等真正貴的 pattern、跨設備差異大

---

## 判讀徵兆

| 訊號                                 | 該檢查的位置                                         |
| ------------------------------------ | ---------------------------------------------------- |
| 使用者操作後輕微跳動或卡頓           | DevTools Performance 看 Layout 區塊                  |
| 動畫不順                             | 確認動畫屬性是 transform / opacity 而非 width / left |
| Layout shift 警告                    | 找出觸發 layout 的元素、量穩定性                     |
| Console 出現「Forced reflow」warning | 找寫後立刻讀的 DOM pattern                           |

**核心原則**：Reflow 是 layout 系統的正常運作、不是要消滅的敵人。盤點時量化看哪些值得優化、哪些可以接受。
