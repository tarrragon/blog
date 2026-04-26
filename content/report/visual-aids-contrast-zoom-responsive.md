---
title: "視覺輔助：對比度、放大、字型 zoom 的 layout 適配"
date: 2026-04-25
weight: 40
description: "色弱、低對比敏感、低視力使用者跟一般使用者「看到的不是同一個 UI」 — 對比度足夠嗎、絕對定位元件在放大模式下是否可達、字型放大 200% 後 layout 還好嗎。本文盤點視覺呈現面的 a11y 風險點。"
tags: ["report", "事後檢討", "Accessibility", "CSS", "工程方法論"]
---

## 核心原則

**視覺輔助使用者跟一般使用者「看到的不是同一個 UI」 — 對比度、放大倍率、字型尺寸調整都會把版面變形。** 設計時先盤點「在這些變形下、UI 還能用嗎」、不需要等到使用者反映。WCAG 提供量化標準、可以在開發階段驗證。

> 本篇焦點：**視覺呈現面的 a11y**（對比 / 放大 / 字型 zoom）。
> - **鍵盤使用者的 a11y**（focus indicator / tab 順序）由 [#52 鍵盤可達性](../keyboard-accessibility/) 處理
> - **行動 / motor 使用者的 a11y**（hit target / 點擊精準度）由 [#53 Motor 可達性](../motor-accessibility-hit-target/) 處理

---

## 為什麼視覺輔助需要獨立盤點

### 商業邏輯

視覺輔助使用者的需求多元：

| 情境                     | 需求                      |
| ------------------------ | ------------------------- |
| 色弱（colour blindness） | 不依賴顏色區分資訊        |
| 低對比敏感               | 文字 vs 背景對比足夠      |
| 低視力（low vision）     | 字大、可放大、layout 不破 |
| 老花、暫時視覺受限       | 字大、清楚的視覺層次      |

每類觸發不同的 CSS 行為。一個 UI 在標準視窗看起來 OK、放大 200% 後可能：

- 字超出容器
- Absolute 定位元件跑到視窗外
- 對比度被覆蓋（dark mode / 高對比模式）

WCAG（Web Content Accessibility Guidelines）提供量化標準（對比度 AA ≥ 4.5:1、放大 200% 不橫向 scroll）— 可在開發階段測量。

### 視覺呈現的三維度

| 維度      | 變形方式                                 | 開發階段檢查方法                                      |
| --------- | ---------------------------------------- | ----------------------------------------------------- |
| 色彩      | dark mode / 高對比模式 / 色弱模擬        | DevTools Contrast Ratio + Emulate Vision Deficiencies |
| 整體 zoom | 瀏覽器 zoom 200% / OS 放大鏡             | Cmd + 5 次、macOS Zoom 4x                             |
| 字型 zoom | OS Display Scale（只放大字型不放大 box） | OS 設定 Larger Text                                   |

三維度獨立、要分開檢查 — 一維度過 ≠ 全部過。

---

## 風險點 1：搜尋結果 highlight 對比度

**位置**：Pagefind 高亮命中關鍵字（黃底）。

**判讀**：

- 預設 `--pagefind-ui-tag` = `#eeeeee`（淺灰）— 文字 `#393939`（深灰）、對比 ~9:1、合格
- 但搜尋頁 dark mode 下、theme 可能讓文字變淺色 — 對淺底要驗證
- 色弱使用者看不出哪個字是 highlight（若僅靠顏色區分）

**WCAG 標準**：

| 等級                           | 對比度要求 |
| ------------------------------ | ---------- |
| AA 一般文字                    | ≥ 4.5:1    |
| AA 大字（≥ 18pt 或 14pt bold） | ≥ 3:1      |
| AAA 一般文字                   | ≥ 7:1      |

**第一個該查的**：用 Chrome DevTools 的 Contrast Ratio 工具量 highlight 區域的「背景 vs 文字」對比。不足則覆寫 `--pagefind-ui-tag` 變數。

**雙重保險**：除了顏色、加 underline 或 bold 區分 highlight — 色弱使用者不靠顏色也能辨識。

---

## 風險點 2：Absolute 定位元件在放大模式下跑到視窗外

**位置**：`.search-filter-slot { position: absolute; right: calc(100% + 2rem); }`。

**判讀**：

- Absolute 定位相對 main 計算
- 使用者用 OS 螢幕放大鏡（macOS Zoom）放大 4x 看 main 中央
- main 仍在視窗範圍、但 absolute filter 在 main 左外側 — 放大 4x 後可能完全跑到視窗左邊看不見

**症狀**：低視力使用者用放大鏡時、不知道 filter 存在、無法操作。

**第一個該查的**：用 macOS 的 Zoom 功能（System Settings > Accessibility > Zoom）放大 4x、看 filter 是否仍在可達範圍。

**修正方向**：

| 策略                                    | 機制                                                 |
| --------------------------------------- | ---------------------------------------------------- |
| 放大模式 fallback 到 mobile layout      | `@media` 偵測 prefers-reduced-motion / 高 zoom level |
| Filter 移到頁面內 flow（不用 absolute） | 跟主要內容一起 reflow、不會跑外                      |
| 加 floating button「展開 filter」       | 任何 zoom level 都可達                               |

詳細展開由 [#43 最小必要範圍](../minimum-necessary-scope-is-sanity-defense/) + [#27 runtime 量測模式統一](../runtime-measurement-unification/) 補充。

---

## 風險點 3：字型放大 200% 後 layout 破壞

**位置**：所有寫死 px 高度的元素（H1、search input、filter slot padding）。

**判讀**：

- 使用者用瀏覽器 zoom（Cmd +）通常等比放大 — 字 + box 一起放大、layout 不破
- 但 OS Display Scale（macOS Display > Larger Text）只放大字型不放大 box — 字撐爆寫死的 64px 高度

當 H1 字撐到 80px、寫死 height: 64px 的 box — 字被裁切。

**症狀**：低視力使用者開啟「文字放大」設定、UI 字被裁。

**第一個該查的**：開瀏覽器 zoom 200%、看 layout 是否變橫向 scroll（破壞）或仍 reflow（OK）。

**WCAG 標準**：1.4.4 Resize text — zoom 至 200% 時不需要橫向 scroll。

**修正方向**：

| 策略                                     | 機制                                                                      |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| 用 `min-height` 取代 `height`            | box 可隨字撐高、不裁切                                                    |
| 用 `em` / `rem` 取代 `px`                | 跟字型一起 scale                                                          |
| 用 ResizeObserver 量字型實際高度寫回變數 | 跟 [#27 runtime 量測模式統一](../runtime-measurement-unification/) 同框架 |

預設用 `min-height` + 相對單位、特殊精準對齊才用 ResizeObserver。

---

## 設計取捨：layout 適應字型放大

當「對齊精度」與「字型放大相容性」衝突、四種做法：

### A：用 `min-height` + 相對單位（這個專案的預設）

- **機制**：`min-height: 4rem`、box 隨字撐高、用 `em` / `rem` 跟著 scale
- **選 A 的理由**：字型放大時 layout 自然 reflow、不裁切
- **適合**：絕大多數 UI 元素、不需要極精準對齊
- **代價**：對齊精度受字型 metrics 影響、難以做 pixel-perfect 對齊

### B：寫死 `height` + ResizeObserver 量測補償

- **機制**：`height: 64px`、用 ResizeObserver 量實際渲染高度寫回 CSS 變數、其他依賴此值的元素跟著調
- **跟 A 的取捨**：B 達到 pixel-perfect 對齊、A 信任 reflow；B 多一層 JS 量測、A 純 CSS
- **B 比 A 好的情境**：對齊精度是 UX 核心（搜尋頁的視覺對齊）、字型可預期

### C：寫死 `height` + 不處理字型放大

- **機制**：`height: 64px`、不管字型放大
- **成本特別高的原因**：字型放大時 UI 被裁切、低視力使用者無法用
- **C 才合理的情境**：UI 不會被字型放大影響（純圖示、無文字）

### D：用 `clamp(min, ideal, max)` 限制字型大小

- **機制**：字型 `font-size: clamp(0.875rem, 1rem, 1.125rem)`、限制使用者放大範圍
- **跟 A/B/C 的取捨**：D 主動限制字型放大範圍、違反 WCAG 1.4.4
- **D 是反模式**：違反 WCAG 1.4.4 — 強制限制字型放大是反 a11y、低視力使用者完全無法調整

---

## 開發階段檢查清單

每個視覺輔助項目對應一個檢查動作：

| 檢查        | 動作                                                     | WCAG 等級 |
| ----------- | -------------------------------------------------------- | --------- |
| 對比度      | DevTools Inspect Element > Contrast Ratio 看每個文字區域 | AA 必要   |
| 色彩可辨    | DevTools Rendering > Emulate Vision Deficiencies         | AA 建議   |
| Zoom 200%   | 瀏覽器 Cmd + 5 次、看是否仍可用、無橫向 scroll           | AA 必要   |
| OS 字型放大 | macOS Display > Text Size > 大、看 layout                | AA 建議   |
| 螢幕放大鏡  | macOS Zoom 4x、看絕對定位元件是否在可達範圍              | AA 建議   |

每個 ~30 秒、開發完成前跑一輪、抓常見問題。

---

## 設計取捨：色彩區分策略

當資訊需要區分（hit / miss、selected / unselected）、四種做法：

### A：顏色 + 形狀 / 位置雙重區分（這個專案的預設）

- **機制**：highlight 用黃底 + bold；selected radio 用色彩 + ✓ 圖示
- **選 A 的理由**：色弱使用者不靠顏色仍能辨識
- **適合**：絕大多數需要區分資訊的場景
- **代價**：UI 多一層視覺裝飾

### B：純顏色區分

- **機制**：紅色 = 錯、綠色 = 對
- **跟 A 的取捨**：B 視覺乾淨、A 對色弱友善；B 違反 WCAG 1.4.1 Use of Color
- **B 是反模式**：違反 WCAG 1.4.1 Use of Color（合規層） — 色弱使用者完全無法區分對 / 錯

### C：純形狀 / 位置區分（無顏色）

- **機制**：用 ✓ / ✗ / 位置區分、不靠顏色
- **跟 A 的取捨**：C 對色彩無關、A 對視力正常使用者更直覺
- **C 比 A 好的情境**：列印 / 黑白渲染環境

### D：使用者可自訂顏色

- **機制**：透過 CSS variable 讓使用者覆寫色彩
- **跟 A 的取捨**：D 提供無限彈性、實作成本高
- **D 才合理的情境**：core a11y 工具（如 reading mode）

---

## 跟其他原則的關係

| 抽象層原則                                                        | 關係                                                 |
| ----------------------------------------------------------------- | ---------------------------------------------------- |
| [#43 最小必要範圍](../minimum-necessary-scope-is-sanity-defense/) | 字型放大下 layout 適配是「不依賴特定渲染條件」的應用 |
| [#44 SSoT](../single-source-of-truth/)                            | CSS 變數提供主題切換、變數住址唯一才能正確覆寫色彩   |

---

## 判讀徵兆

| 訊號                               | 該檢查的位置                                                    |
| ---------------------------------- | --------------------------------------------------------------- |
| 色弱使用者反映找不到資訊           | DevTools Contrast Ratio + Emulate Vision Deficiencies           |
| 低視力使用者反映 UI 跑到視窗外     | 用螢幕放大鏡放 4x 確認 absolute 元件位置                        |
| 字型放大後 UI 破                   | 用瀏覽器 zoom 200% 與 OS text size 雙測                         |
| Dark mode 下文字看不清             | 該主題的對比度未驗證、補測                                      |
| 「色弱使用者反正不多」當不做的理由 | 視覺輔助使用者通常不會反映、只默默離開 — 量化檢查不靠使用者通報 |

**核心原則**：視覺輔助使用者用的是「同一份程式、不同的 viewport / colour / scale」。WCAG 提供量化標準、開發階段可測 — 等使用者反映晚了。
