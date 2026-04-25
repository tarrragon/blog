---
title: "置中元件與絕對定位元件並存：用疊層而非排擠"
date: 2026-04-25
weight: 8
description: "中央欄需要置中、側邊元件需要指定位置 — 兩者要共存，關鍵是讓側邊元件用 absolute 跳出 layout 流，中央欄完全感知不到它。本文展開疊層式並存的設計。"
tags: ["report", "事後檢討", "CSS", "Layout", "工程方法論"]
---

## 核心原則

**置中元件與指定位置元件共存，正確做法是讓兩者位於不同 layout 層。** Layout 流負責「以內容驅動的尺寸與置中」；絕對定位負責「貼在 layout 流之上的固定位置元件」。兩者用疊層共存、不互相排擠。

---

## 為什麼排擠式做法行不通

### 商業邏輯

排擠式：把兩個元件放進同一個 grid / flex container、各佔一個欄位。問題在於「容器寬度有限、加一個欄位就壓縮另一個」 — 中央欄想置中時，加 sidebar 後整個 layout 重新分佈、中央欄被推到非置中位置。

疊層式：sidebar 用 `position: absolute` 從 layout 流跳出 — 中央欄看不到 sidebar、繼續按自己的規則置中。

### 兩種共存模式比較

| 模式                   | 中央欄置中                     | 維護成本                   | 適用情境                             |
| ---------------------- | ------------------------------ | -------------------------- | ------------------------------------ |
| 排擠式（同 layout 流） | 受 sidebar 影響、需要重算      | 低 — 純 CSS                | 兩個元件都要自然撐開                 |
| 疊層式（absolute）     | 不受影響、永遠按 viewport 置中 | 中 — absolute 需要定位基準 | 中央欄要嚴格置中、sidebar 是「附加」 |

選擇疊層式的時機：**中央欄的位置是設計重點、sidebar 是補充**。本案搜尋頁的 main 是內容主體、filter 是輔助 — 適合疊層。

---

## 這次任務的實際做法

### 觀察

搜尋頁 desktop layout：

- `<main>` 寬度 70ch、theme 預設 `margin-inline: auto` 置中
- 想加 filter sidebar 在 main 左外側、寬度 400px

### 判讀

把 filter 放進 main 的 grid（變成 main 的子 column），main 內容會被推到右半邊、不再置中。

讓 filter 用 `position: absolute` 相對 main 定位 — main 完全不知道 filter 存在、繼續置中。filter 在 main 外側「貼著」main 的左邊緣。

### 執行

```css
body.page-search main#main-content {
  position: relative;   /* filter 的 offset parent */
  /* main 的 max-width: 70ch 與 margin-inline: auto 由 theme 提供，不動 */
}

.search-filter-slot {
  position: absolute;
  top: 0;
  right: calc(100% + 2rem);   /* main 的左外側、間距 2rem */
  width: 400px;
}
```

`right: calc(100% + 2rem)` 的含義：filter 的右邊緣 = main 左邊緣 - 2rem。filter 從這個 anchor 往左展開 400px。

main 永遠按 viewport 置中、filter 永遠貼在 main 左外側。

---

## 疊層共存的三個關鍵要素

### 1. Offset parent 的選擇

絕對定位元件的座標相對於「最近的 positioned ancestor」。要讓 sidebar 跟著 main 一起移動（不要跟 viewport 走），就把 main 設為 `position: relative` 當作 offset parent。

```css
body.page-search main { position: relative; }
.search-filter-slot { position: absolute; /* 相對 main */ }
```

### 2. Anchor 點的選擇

`right: calc(100% + 2rem)`、`left: -432px`、`right: 100%; margin-right: 2rem` 三種寫法視覺上等價。選擇可讀性最高的 — 通常是 `right: calc(100% + 2rem)`，意義最直接（「我的右緣 = parent 寬度 + 2rem 之外」）。

### 3. 物理空間檢查

絕對定位不檢查 viewport 邊界 — sidebar 可能被推到 viewport 外。需要在 breakpoint 確認「viewport 夠寬時才顯示 sidebar」：

```css
.search-filter-slot { display: none; }
@media (min-width: 1400px) {
  .search-filter-slot { display: block; }
}
```

物理空間預算的細節參見〈跨 viewport 雙模式 UI 的物理空間預算〉。

---

## 內在屬性比較：兩種共存做法

| 屬性             | 排擠式（grid / flex）         | 疊層式（absolute）                  |
| ---------------- | ----------------------------- | ----------------------------------- |
| 中央欄位置       | 隨 sidebar 寬度變動           | 不受影響、嚴格置中                  |
| Sidebar 寬度限制 | 來自 grid container           | 來自 viewport（需 breakpoint 控制） |
| Layout 重算成本  | 改 sidebar 寬度時 main 跟著動 | main 永遠不動                       |
| 適用情境         | 兩個元件都要自然撐開          | 中央嚴格置中、sidebar 附加          |

選擇順序：**先確認中央欄的位置要求**。要嚴格置中 → 疊層式；可隨 sidebar 浮動 → 排擠式。

---

## 正確概念與常見替代方案的對照

### Layout 流與絕對定位是兩個獨立層

**正確概念**：把要嚴格置中的元件留在 layout 流、把附加元件用 absolute 浮在 layout 流之上。兩者透過 offset parent 連結但不互相影響。

**替代方案的不足**：把所有元件都放進同一 grid 試圖一次解決 — 中央欄的位置依賴 sidebar 的存在、改 sidebar 設計就要重算 main 的位置、互相牽動。

### Absolute 元件的座標基準要明確

**正確概念**：absolute 元件透過 `position: relative` ancestor 建立座標系。把該 ancestor 選定為「跟 absolute 元件移動同步的參考點」。

**替代方案的不足**：忘了設 `position: relative`，absolute 元件相對 viewport 計算、跟著 viewport 走、跟 main 的位置脫鉤。

### 物理空間預算與疊層分開處理

**正確概念**：疊層式解決「位置關係」；物理空間預算解決「viewport 夠不夠寬」。兩者獨立、各自有對應規則。

**替代方案的不足**：把 viewport 寬度檢查塞進 absolute 定位的 calc — sidebar 可能溢出 viewport 也仍然顯示、視覺破壞。

---

## 判讀徵兆

| 訊號                                         | 可能的根因             | 第一個該嘗試的動作                          |
| -------------------------------------------- | ---------------------- | ------------------------------------------- |
| 加了 sidebar 後中央內容不再置中              | 用了排擠式、中央欄被推 | 改用 absolute、main 設 `position: relative` |
| Absolute sidebar 跟著 viewport 跑、不貼 main | 沒設 offset parent     | 給 main 加 `position: relative`             |
| Sidebar 在窄 viewport 溢出畫面               | 沒做物理空間檢查       | 加 breakpoint、寬度不夠時 `display: none`   |
| 改 sidebar 寬度時要回頭調 main 樣式          | 排擠式造成 layout 耦合 | 改用疊層、main 永遠不需要因 sidebar 改      |

**核心原則**：兩個元件的視覺關係用疊層描述、不用排擠描述。疊層 = 兩層獨立 = 改一邊不影響另一邊。
