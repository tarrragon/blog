---
title: "表單 UX 模式"
date: 2026-06-19
description: "表單輸入的驗證時機、auto-fill 支援、錯誤回饋設計 — 和 terminal 輸入的決策維度相同但選項不同"
weight: 3
tags: ["ux-design", "input", "form", "validation", "mobile"]
---

表單輸入和 terminal 輸入用同一套四維度決策框架（keyboard type / submit model / IME policy / special keys），但每個維度的選項和取捨方向不同。表單場景的使用者輸入的是結構化但自然語言為主的內容 — 姓名、email、地址 — 手機鍵盤的自動行為在這個場景中大部分是幫助。

## Keyboard type 的選擇

表單的每個欄位應該使用最適合該欄位內容的鍵盤。正確的 keyboard type 減少使用者在鍵盤上找按鍵的時間，也讓自動填入和驗證更準確。

| 欄位     | Keyboard type                    | 理由                                       |
| -------- | -------------------------------- | ------------------------------------------ |
| Email    | emailAddress                     | 有 `@` 和 `.` 快捷鍵                       |
| 電話號碼 | phone                            | 只顯示數字和 `+` `-`                       |
| URL      | url                              | 有 `.com` 快捷鍵和 `/` 鍵                  |
| 密碼     | visiblePassword                  | 關閉自動校正，保留字元可見控制             |
| 搜尋     | text                             | 一般文字，可搭配 `textInputAction: search` |
| 數字金額 | numberWithOptions(decimal: true) | 數字鍵盤加小數點                           |

## 驗證時機

表單驗證的時機影響使用者的操作流暢度和錯誤修正效率。

### 即時驗證（on change）

每次輸入變化時驗證。適合格式明確的欄位（email 格式、手機號碼長度）。即時驗證在使用者輸入過程中就能回饋格式錯誤，不需要等到送出。

即時驗證的風險是過早報錯。使用者正在輸入 email 地址 `user@` 時，缺少 domain 部分 — 這個時候報「email 格式錯誤」對使用者沒有幫助。解法是在欄位失去焦點（on blur）時才顯示錯誤，輸入過程中只顯示通過的驗證（例如勾號表示格式正確）。

### 送出時驗證（on submit）

使用者按送出按鈕時統一驗證所有欄位。適合需要多欄位交叉驗證的場景（密碼確認、日期範圍）。

送出時驗證的風險是使用者填完整張表單才知道哪裡有問題。在欄位多的表單中，使用者需要回頭找到錯誤欄位修正 — 用 scroll 定位和欄位 highlight 減輕這個成本。

### 混合策略

格式驗證用即時（on blur）、業務邏輯驗證用送出時。Email 格式在失去焦點時檢查，「email 是否已被註冊」在送出時呼叫 API 檢查。

## Auto-fill 支援

手機系統（iOS AutoFill、Android Autofill）可以自動填入使用者已儲存的資訊（姓名、地址、信用卡）。App 需要正確標記每個欄位的語意類型（`autofillHints`），系統才能匹配正確的儲存值。

正確標記的欄位讓使用者一鍵填入而非手動輸入 — 在 mobile 上減少的打字量直接轉化為轉換率提升。

## 錯誤回饋

錯誤訊息的位置和內容影響使用者修正錯誤的效率。

**位置**：錯誤訊息應該緊跟在對應欄位下方，而非集中在表單頂部或底部。使用者需要在看到錯誤的同時看到對應的欄位，不需要來回比對。

**內容**：錯誤訊息應該說明「期望什麼」而非「哪裡錯了」。「請輸入有效的 email 地址」比「email 格式無效」提供更多行動指引。

**視覺**：錯誤欄位的邊框變色（通常紅色）讓使用者在視覺掃描時快速定位。搭配錯誤文字使用，不要只靠顏色（色盲使用者）。

## 下一步路由

- 搜尋場景的輸入設計 → [搜尋 UX 模式](/ux-design/03-input-mechanism/search-ux-pattern/)
- 四維度決策表總覽 → [輸入機制決策表](/ux-design/03-input-mechanism/four-dimension-decision/)
- 安全敏感欄位的 IME 控制 → [IME 安全 checklist](/ux-design/03-input-mechanism/ime-security-checklist/)
