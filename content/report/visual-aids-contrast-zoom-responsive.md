---
title: "視覺輔助情境：對比度、縮放、響應式 zoom"
date: 2026-04-25
weight: 40
description: "色弱、低視力、放大模式的使用者怎麼用搜尋頁 — 對比度足夠嗎、放大時 absolute filter 是否還在可達範圍、字型放大 200% 後 layout 還好嗎。本文盤點視覺輔助場景的風險點。"
tags: ["report", "事後檢討", "Accessibility", "CSS", "工程方法論"]
---

## 核心原則

**視覺輔助使用者跟一般使用者「看到的不是同一個 UI」 — 對比度、放大倍率、字型尺寸調整都會把版面變形。** 設計時先盤點「在這些變形下、UI 還能用嗎」、不需要等到使用者反映。WCAG 提供量化標準、可以在開發階段驗證。

---

## 為什麼視覺輔助場景需要獨立盤點

### 商業邏輯

視覺輔助使用者的需求多元：

| 情境                     | 需求                      |
| ------------------------ | ------------------------- |
| 色弱（colour blindness） | 不依賴顏色區分資訊        |
| 低對比敏感               | 文字 vs 背景對比足夠      |
| 低視力（low vision）     | 字大、可放大、layout 不破 |
| 老花、暫時視覺受限       | 字大、清楚的 hit target   |

每類觸發不同的 CSS 行為。一個 UI 在標準視窗看起來 OK、放大 200% 後可能：

- 字超出容器
- Absolute 定位元件跑到視窗外
- Hit target 變小、難點

WCAG（Web Content Accessibility Guidelines）提供量化標準（對比度、放大倍率、字型可調整）— 可在開發階段測量。

### 三類視覺輔助情境

| 情境        | 開發階段檢查方法                          |
| ----------- | ----------------------------------------- |
| 色彩對比    | DevTools Contrast Ratio 工具              |
| 字型放大    | 瀏覽器 zoom 200% / 用 OS 的 Display Scale |
| Layout 適配 | 響應式設計、reflow 而非橫向 scroll        |

---

## 搜尋頁的具體風險點

### 風險 1：搜尋結果 highlight 對比度

**位置**：Pagefind 高亮命中關鍵字（黃底）。

**判讀**：

- 預設 `--pagefind-ui-tag` = `#eeeeee`（淺灰）— 文字 `#393939`（深灰）、對比 ~9:1、合格
- 但搜尋頁 dark mode 下、theme 可能讓文字變淺色 — 對淺底要驗證

**症狀**：色弱使用者看不出哪個字是 highlight。

**第一個該查的**：用 Chrome DevTools 的 Contrast Ratio 工具量 highlight 區域的「背景 vs 文字」對比。WCAG AA 要求 ≥ 4.5:1（一般文字）/ ≥ 3:1（大字）。不足則覆寫 `--pagefind-ui-tag` 變數。

### 風險 2：Filter slot 在放大模式下跑到視窗外

**位置**：`.search-filter-slot { position: absolute; right: calc(100% + 2rem); }`。

**判讀**：

- Absolute 定位相對 main 計算
- 使用者用 OS 螢幕放大鏡（macOS Zoom）放大 4x 看 main 中央
- main 仍在視窗範圍、但 absolute filter 在 main 左外側 — 放大 4x 後可能完全跑到視窗左邊看不見

**症狀**：低視力使用者用放大鏡時、不知道 filter 存在、無法操作。

**第一個該查的**：用 macOS 的 Zoom 功能（System Settings > Accessibility > Zoom）放大 4x、看 filter 是否仍在可達範圍。若否、考慮放大模式自動 fallback 到 mobile（drawer 內 filter）。

### 風險 3：字型放大 200% 後 layout 破壞

**位置**：所有寫死 px 高度的元素（H1、search input、filter slot padding）。

**判讀**：

- 使用者用瀏覽器 zoom（Cmd +）通常等比放大、layout 不破
- 但 OS Display Scale（macOS Display > Larger Text）只放大字型不放大 box — 字撐爆寫死的 64px 高度

當 H1 字撐到 80px、寫死 height: 64px 的 box — 字被裁切。

**症狀**：低視力使用者開啟「文字放大」設定、UI 字被裁。

**第一個該查的**：開瀏覽器 zoom 200%、看 layout 是否變橫向 scroll（破壞）或仍 reflow（OK）。WCAG 要求 zoom 至 200% 時不需要橫向 scroll。

### 風險 4：Hit target 太小

**位置**：scope UI 的 radio buttons。

**判讀**：

- WCAG 2.5.5（AAA）建議互動元素 hit target ≥ 44×44px
- Native `<input type="radio">` 在桌面 ~13×13px、行動裝置 24×24px
- label 包住 input + 文字、整個 label 可點 — 提升 hit target

**症狀**：行動裝置使用者點擊精準度不足、誤點旁邊選項。

**第一個該查的**：量 label 整體（含 padding）的高度與寬度。當前實作 `padding: 0.4rem 0.75rem` 約 36px 高、可改 `0.625rem 1rem` 達到 44px。

### 風險 5：Focus indicator 可見度

**位置**：tab focus 到 search input、scope radio、filter checkbox 等元素。

**判讀**：

- 瀏覽器預設 focus outline（藍色 2px）
- 某些 theme 用 `outline: 0` 移除 — 鍵盤使用者迷失
- 自訂 outline 要對比足夠（WCAG 2.4.7）

**症狀**：鍵盤使用者 tab 過去看不到 focus 在哪。

**第一個該查的**：用 keyboard tab 過所有互動元素、確認每個都有可見 focus。若無、加 `:focus-visible { outline: 2px solid currentColor; }`。

---

## 內在屬性比較：四種視覺輔助考量

| 考量                           | WCAG 等級 | 開發階段可測             |
| ------------------------------ | --------- | ------------------------ |
| 對比度（4.5:1 一般、3:1 大字） | AA 必要   | 是 — Contrast Ratio 工具 |
| Zoom 200% 不需橫向 scroll      | AA 必要   | 是 — 瀏覽器 zoom         |
| Hit target 44×44               | AAA 建議  | 是 — DevTools Box Model  |
| Focus indicator 可見           | AA 必要   | 是 — 鍵盤 tab 測試       |

優先順序：**先解 AA（必要）、再評估 AAA（建議）**。

---

## 開發階段可量化檢查清單

每個視覺輔助項目對應一個檢查動作：

| 檢查            | 動作                                                     |
| --------------- | -------------------------------------------------------- |
| 對比度          | DevTools Inspect Element > Contrast Ratio 看每個文字區域 |
| Zoom 200%       | 瀏覽器 Cmd + 5 次、看是否仍可用、無橫向 scroll           |
| OS 字型放大     | macOS Display > Text Size > 大、看 layout                |
| 螢幕放大鏡      | macOS Zoom 4x、看絕對定位元件是否在可達範圍              |
| Hit target      | DevTools Box Model 量 interactive 元素的 padding box     |
| Focus indicator | 鍵盤 tab 過所有元素、確認 focus 可見                     |

每個 ~30 秒、開發完成前跑一輪、抓常見問題。

---

## 正確概念與常見替代方案的對照

### 視覺輔助情境用 WCAG 量化

**正確概念**：用 WCAG 標準（對比度、放大倍率、hit target size）量化檢查、不靠主觀判斷。

**替代方案的不足**：用「看起來 OK」做標準 — 開發者通常視力正常、感受不到視覺輔助使用者的痛點。

### 開發階段檢查、不等使用者反映

**正確概念**：每個視覺輔助項目開發完跑一次檢查（30 秒）、抓出明顯問題。

**替代方案的不足**：等使用者反映才修 — 多數使用者不會反映、只是默默離開。

### 放大模式優先考慮 reflow

**正確概念**：頁面放大時 reflow（內容折行、layout 適配）、避免橫向 scroll。

**替代方案的不足**：放大時出現橫向 scroll — 使用者要左右捲動才能讀完一行、體驗極差。

---

## 判讀徵兆

| 訊號                                 | 該檢查的位置                             |
| ------------------------------------ | ---------------------------------------- |
| 色弱使用者反映找不到資訊             | DevTools Contrast Ratio 量所有顏色組合   |
| 低視力使用者反映 UI 跑到視窗外       | 用螢幕放大鏡放 4x 確認 absolute 元件位置 |
| 鍵盤使用者反映 tab 後不知 focus 在哪 | 確認每個互動元素都有可見 focus indicator |
| 行動使用者誤點                       | 量 hit target、< 44px 加 padding         |
| 字型放大後 UI 破                     | 用瀏覽器 zoom 200% 與 OS text size 雙測  |

**核心原則**：視覺輔助使用者用的是「同一份程式、不同的 viewport / colour / scale」。WCAG 提供量化標準、開發階段可測 — 等使用者反映晚了。
