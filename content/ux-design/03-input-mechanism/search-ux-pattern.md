---
title: "搜尋 UX 模式"
date: 2026-06-19
description: "Debounce / instant / suggestion 三種搜尋模式的取捨 — 和輸入機制的 submit model 維度直接相關"
weight: 4
tags: ["ux-design", "input", "search", "debounce", "mobile"]
---

搜尋輸入的核心決策是「使用者輸入到什麼程度觸發搜尋」。這和 terminal 輸入的 submit model 維度相同 — 差別在 terminal 場景的選項是「整行 vs 逐字元」，搜尋場景的選項是「按送出 vs 即時 vs debounce」。

## 三種觸發模式

### 按送出觸發

使用者打完搜尋詞、按搜尋按鈕後觸發一次搜尋。最簡單的模式 — 一次搜尋、一次 API 呼叫、一次結果顯示。

適合搜尋成本高的場景：資料庫全文搜尋、外部 API 呼叫（有速率限制或費用）、搜尋結果需要複雜運算。

### 即時觸發（instant）

使用者每輸入一個字元就觸發搜尋。結果即時更新，使用者可以在輸入過程中看到搜尋結果逐漸精確。

適合搜尋成本低的場景：client 端的本地過濾、記憶體內的資料集篩選、已快取的少量資料。

即時觸發在搜尋成本高的場景會產生問題：使用者輸入 `hello` 的過程中觸發五次 API 呼叫（`h`、`he`、`hel`、`hell`、`hello`），前四次的結果在使用者看到之前就被覆蓋。浪費的 API 呼叫增加 server 負載和使用者的網路流量。

### Debounce 觸發

使用者停止輸入一段時間後（通常 300-500ms）觸發搜尋。平衡即時回饋和 API 呼叫次數 — 使用者連續打字時不觸發，停下來時觸發一次。

[Debounce](/ux-design/knowledge-cards/debounce/) 是遠端搜尋場景的常見選擇（搜尋框用 trailing-edge 語意 — 等使用者停止輸入才觸發）。延遲時間的設定是 UX trade-off：太短（100ms）接近即時觸發，API 呼叫次數多；太長（1000ms）使用者感覺到明顯延遲。300-500ms 是多數場景的合理區間。

## 搜尋結果的顯示

### Suggestion list（建議列表）

在搜尋框下方即時顯示候選結果。使用者可以點選候選項完成搜尋，不需要打完整個搜尋詞。

Suggestion list 適合搜尋詞有限且可列舉的場景（城市名、產品名、使用者名）。搜尋詞無限（全文搜尋）時 suggestion list 的候選項品質依賴搜尋演算法。

### 結果頁

使用者送出搜尋後導航到獨立的結果頁面。適合結果量大、需要分頁、每筆結果需要較多空間展示的場景。

### 即時過濾（filter）

在現有列表上即時隱藏不符合搜尋條件的項目，不導航到新頁面。適合「在已經看得到的清單中找到特定項目」的場景。

## keyboard type 和 textInputAction

搜尋框的 keyboard type 通常用 `text`（一般文字），搭配 `textInputAction: search` 讓鍵盤的 Enter 鍵顯示搜尋圖示（放大鏡）而非換行或送出圖示。

這個細節影響使用者的操作直覺 — 看到搜尋圖示的按鈕，使用者知道按下去會觸發搜尋；看到換行圖示，使用者可能猶豫按下去會不會換行。

## 下一步路由

- 四維度決策表總覽 → [輸入機制決策表](/ux-design/03-input-mechanism/four-dimension-decision/)
- Terminal 場景的 submit model → [Terminal app 輸入設計](/ux-design/03-input-mechanism/terminal-input-design/)
- 表單場景的驗證設計 → [表單 UX 模式](/ux-design/03-input-mechanism/form-ux-pattern/)
