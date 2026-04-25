---
title: "Motor 可達性：hit target、間距、誤點防護"
date: 2026-04-25
weight: 53
description: "Hit target 太小會讓行動裝置使用者誤點、motor 障礙使用者更甚。WCAG AAA 建議 ≥ 44×44px、間距足夠避免誤觸。本文展開 hit target 設計與相關 motor a11y 風險點。"
tags: ["report", "事後檢討", "Accessibility", "Touch", "Mobile", "工程方法論"]
---

## 核心原則

**Hit target ≥ 44×44px、相鄰互動元素之間有間距、避免「精準瞄準」需求。** Motor accessibility 處理的不是視覺、是「手能否準確點擊」 — 行動裝置使用者、年長使用者、motor 障礙使用者都受益。設計時優先擴大 padding、不是縮小視覺。

> 本篇焦點：**motor 可達性**。
> - **視覺呈現面的 a11y**由 [#40 視覺輔助](visual-aids-contrast-zoom-responsive/) 處理
> - **鍵盤使用者的 a11y**由 [#52 鍵盤可達性](keyboard-accessibility/) 處理

---

## 為什麼 motor 可達性需要獨立盤點

### 使用者類型

| 使用者 | 為什麼 hit target 重要 |
|---|---|
| 行動裝置使用者 | 手指比滑鼠粗、需要更大目標 |
| 年長使用者 | 手部精準度下降 |
| Motor 障礙使用者 | Tremor / 手部協調困難 |
| 暫時受限使用者（拿東西單手操作、晃動環境） | 短期內精準度下降 |

最後一類包含「正常使用者在某些情境」 — motor a11y 的設計對全體使用者都有價值。

### 失敗模式

| 失敗 | 表現 | 影響範圍 |
|---|---|---|
| Hit target < 24px | 行動裝置上難點 | 多數行動使用者 |
| 相鄰互動元素間距不足 | 誤觸隔壁 | 手指粗 / motor 障礙者 |
| 需要精準 drag / pinch | 部分 motor 障礙者無法 | motor 障礙者 |
| 短時間內需多次精準操作 | tremor 使用者無法 | tremor 使用者 |

---

## WCAG 標準

| 標準 | 要求 | 等級 |
|---|---|---|
| 2.5.5 Target Size | 互動元素 ≥ 44×44 CSS px | AAA |
| 2.5.8 Target Size (Minimum) | 互動元素 ≥ 24×24 CSS px（除非有間距足夠的等價替代） | AA（WCAG 2.2 新增） |
| 2.5.7 Dragging Movements | 拖拽動作有單擊替代 | AA（WCAG 2.2 新增） |

WCAG 2.2 把 motor a11y 從 AAA 拉到部分 AA — 顯示這類問題的重要性提升。

---

## 風險點 1：Hit target 太小

**位置**：scope UI 的 radio buttons、filter checkbox。

**判讀**：

- WCAG 2.5.5（AAA）建議互動元素 hit target ≥ 44×44px
- Native `<input type="radio">` 在桌面 ~13×13px、行動裝置 24×24px
- label 包住 input + 文字、整個 label 可點 — 提升 hit target

**症狀**：行動裝置使用者點擊精準度不足、誤點旁邊選項。

**第一個該查的**：量 label 整體（含 padding）的高度與寬度。

**修正方向**：

```css
/* 較差 — input 視覺很小、label 文字緊鄰 */
label { display: inline-block; }
input[type="radio"] { width: 13px; height: 13px; }

/* 好 — label 整個區域可點、padding 撐到 44px */
label {
  display: inline-flex;
  align-items: center;
  padding: 0.625rem 1rem;  /* 約 44px 高 */
  cursor: pointer;
}
input[type="radio"] { margin-right: 0.5rem; }
```

關鍵不是把 input 視覺變大、是把可點區域擴大（padding）— 視覺保持精緻、可點區域達標。

---

## 風險點 2：相鄰互動元素間距不足

**位置**：filter checkbox 列、scope radio 列。

**判讀**：

兩個 hit target 緊鄰、即使各自達 44px、相鄰時仍可能誤觸 — WCAG 2.5.8 要求「目標之間有足夠間距」。

**症狀**：使用者想點 A 但點到旁邊的 B。

**修正方向**：

```css
/* 加 gap 確保相鄰元素間距 */
.filter-list {
  display: flex;
  flex-direction: column;
  gap: 8px;  /* 至少 8px 間距 */
}

/* 或用 padding 撐開 */
.filter-list label {
  padding: 0.625rem 1rem;
  margin-bottom: 4px;  /* 加總間距達 8px+ */
}
```

預設 8px 間距 — 比視覺需求多一點、避免誤觸。

---

## 風險點 3：需要精準 drag / pinch 的操作

**位置**：搜尋頁未實作 drag 互動、但若未來加（例如拖拽結果排序、pinch 縮放圖片）。

**判讀**：

WCAG 2.5.7（AA）要求 drag 動作有單擊替代 — 例如「拖拽排序」要有「上移 / 下移」按鈕作為替代。

**症狀**：motor 障礙使用者無法完成 drag 操作。

**修正方向**：

```html
<!-- 主互動：drag -->
<li draggable="true">項目 A</li>

<!-- 必須提供：button 替代 -->
<li>
  項目 A
  <button aria-label="上移">↑</button>
  <button aria-label="下移">↓</button>
</li>
```

對搜尋頁當前實作不適用、但未來加互動時的預警。

---

## 設計取捨：擴大 hit target 的策略

當「視覺精緻度」與「hit target 大小」衝突、四種做法：

### A：視覺保持小、padding 擴大可點區（這個專案的預設）

- **機制**：input 視覺 13px、label padding 撐到 44px
- **選 A 的理由**：視覺精緻 + a11y 達標、兩全
- **適合**：絕大多數互動元素
- **代價**：UI 整體高度增加（每行 44px+）

### B：視覺直接放大到 44px

- **機制**：input width: 44px; height: 44px;
- **跟 A 的取捨**：B 視覺粗、A 視覺精緻；B 在「需要清楚看到」的情境（年長使用者）有價值
- **B 比 A 好的情境**：使用者主要是年長者、視覺辨識比精緻重要

### C：視覺小、不擴 padding（不滿足 a11y）

- **機制**：input 13px、label 緊鄰文字、無 padding
- **成本特別高的原因**：行動使用者誤點、motor 障礙者無法用、違反 WCAG 2.5.8
- **C 才合理的情境**：純 desktop 應用 + 確認使用者群不含行動 / motor — 通常不該假設

### D：用 hover area 擴大命中（hover 才放大）

- **機制**：預設視覺小、hover 時擴大可點區
- **跟 A 的取捨**：D 在 desktop 視覺精緻、hover 反饋也好；行動裝置沒有 hover、D 失敗
- **D 比 A 好的情境**：純 desktop 工具

---

## 設計取捨：誤點防護機制

對「誤點代價高」的操作（刪除 / 提交 / 付款）、四種做法：

### A：直接觸發 + 後續 undo（這個專案的預設、若有此類操作）

- **機制**：點擊立刻執行、提供 undo 機制（例如 toast「已刪除、5 秒內可復原」）
- **選 A 的理由**：常見操作流暢、誤點有救
- **適合**：可逆操作（刪除、移動、隱藏）
- **代價**：實作 undo 機制需要儲狀態

### B：點擊 → 確認對話框

- **機制**：點擊出 confirm dialog「確定要 X 嗎？」
- **跟 A 的取捨**：B 防誤點更強、A 流程更順；B 的成本是「正常使用者也要多一步」
- **B 比 A 好的情境**：不可逆操作（永久刪除、付款）

### C：長按觸發

- **機制**：需要長按 1 秒才觸發、誤點不會
- **跟 A/B 的取捨**：C 對 motor 障礙不友善（需要持續按）、且不直觀
- **C 才合理的情境**：實務上幾乎不存在 — 反 motor a11y

### D：拖到「確認區」

- **機制**：滑動到特定區域才觸發（iOS 拖刪除）
- **跟 A/B 的取捨**：D 對非典型互動使用者不直觀、違反 WCAG 2.5.7（需 button 替代）
- **D 才合理的情境**：搭配 button 替代（drag + button 兩種途徑都行）

---

## 開發階段檢查清單

| 檢查 | 動作 |
|---|---|
| Hit target ≥ 44px | DevTools Box Model 量 interactive 元素的 padding box |
| 相鄰元素間距 ≥ 8px | DevTools 看 gap / margin |
| 行動裝置實測 | DevTools Device Mode + 實機測試 |
| 不可逆操作有確認 | 點擊「刪除」看是否有 confirm |
| Drag 操作有 button 替代 | 任何 drag 互動都有對應 button |

---

## 跟其他原則的關係

| 篇 | 關係 |
|---|---|
| [#40 視覺輔助](visual-aids-contrast-zoom-responsive/) | 互補 — 視覺面 vs 操作面、不同使用者群 |
| [#52 鍵盤可達性](keyboard-accessibility/) | 互補 — 鍵盤是 motor a11y 的一個面向（鍵盤精準度 > 滑鼠 > 觸控）、本篇處理觸控 / 點擊面 |
| [#39 Native HTML 優先於 ARIA role](native-html-over-aria-role/) | 用 native button / input 自動獲得合理 hit area、不需自行設計 |

---

## 判讀徵兆

| 訊號 | 該檢查的位置 |
|---|---|
| 行動使用者反映誤點 | 量 hit target、< 44px 加 padding |
| 「我這個介面只給 desktop 用」 | 行動使用者比例可能比想像高、量化驗證 |
| Drag 互動沒有 button 替代 | 加 button、達 WCAG 2.5.7 |
| 不可逆操作沒有 confirm | 加 confirm dialog |
| Filter list 元素緊鄰、容易誤觸 | 加 gap ≥ 8px |

**核心原則**：Motor a11y 是「手能否準確點擊」 — 不只給 motor 障礙使用者、行動使用者 / 年長者 / 暫時受限使用者都受益。預設 padding 擴 44px、間距 8px、不可逆操作加 confirm — 這些是基礎、不是優化。
