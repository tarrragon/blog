---
title: "每個畫面都需要出口：畫面狀態機設計與 UX 導航的系統性方法"
date: 2026-06-19
draft: false
description: "實機測到某畫面沒有返回或退出按鈕、使用者被困住。根因是企劃沒系統列出每個畫面的狀態與可用操作；用畫面狀態矩陣確保每個狀態都有明確出口。"
tags: ["ux", "flutter", "navigation", "state-machine", "mobile", "terminal"]
---

## 這篇要解決什麼

**使用者連上遠端終端機後、無法返回首頁。**

不是 bug — 是設計遺漏。Terminal 畫面的 `connected` 狀態沒有 disconnect 按鈕也沒有 back 按鈕。`error` 和 `disconnected` 狀態也沒有。使用者被困在畫面裡，唯一的出路是殺掉 app。

這不是「忘記加按鈕」的問題。回頭看企劃文件，§1 操作盤點確實列了「連線失敗顯示無法連線」這個失敗情境，但沒有系統性地問：**這個畫面有幾個狀態？每個狀態能做什麼操作？怎麼離開？**

本文整理畫面狀態機設計的方法、示範用狀態矩陣捕捉導航缺口、歸納 mobile app UX 的三個設計原則。

---

## 實際案例：Terminal 畫面的五個狀態

Terminal 畫面有一個 `TerminalScreenUiState` enum 定義了五個狀態：

```dart
enum TerminalScreenUiState { idle, connecting, connected, error, disconnected }
```

實機測試前、這五個狀態各自的 UI 長這樣：

| 狀態         | 顯示                   | 可用操作                  | 退出路徑 |
| ------------ | ---------------------- | ------------------------- | -------- |
| idle         | 空白（自動開始連線）   | 無                        | **無**   |
| connecting   | 「連線中...」進度指示  | 無                        | **無**   |
| connected    | 終端機畫面 + 工具列    | 打字、Esc/Tab/Ctrl/方向鍵 | **無**   |
| error        | 錯誤訊息 + 重連按鈕    | 重新連線                  | **無**   |
| disconnected | 「連線中斷」+ 重連按鈕 | 重新連線                  | **無**   |

五個狀態、零個退出路徑。使用者一旦進入 Terminal 畫面就出不去。

---

## 問題不在按鈕、在設計方法

加 back 按鈕是 5 分鐘的事。真正的問題是：**企劃階段沒有工具強制你為每個狀態想退出路徑。**

操作盤點表長這樣：

| 操作     | 主情境                                | 失敗情境                                | 前端引導                                   |
| -------- | ------------------------------------- | --------------------------------------- | ------------------------------------------ |
| 日常連線 | Face ID → 讀憑證 → WS 連線 → 雙向 I/O | 辨識失敗；Tailscale 離線；ttyd 認證失敗 | 辨識失敗不讀憑證；連線失敗顯示「無法連線」 |

「前端引導」只有一句話。它沒有被展開成畫面狀態。「連線失敗顯示無法連線」這句話覆蓋了 `error` 狀態的**顯示**，但沒有回答**操作**（重連？返回？）和**退出**（怎麼離開這個畫面？）。

---

## 畫面狀態矩陣

把狀態機設計變成一張表，強制回答每個狀態的四個面向：

| 畫面.狀態             | 顯示            | 可用操作     | 進入條件       | 退出路徑                        |
| --------------------- | --------------- | ------------ | -------------- | ------------------------------- |
| Terminal.idle         | 空白            | —            | 從首頁導航進入 | back → 首頁                     |
| Terminal.connecting   | 進度指示        | —            | 自動觸發連線   | back → 首頁（取消連線）         |
| Terminal.connected    | 終端機 + 工具列 | 打字、特殊鍵 | WS 連線成功    | disconnect → idle；back → 首頁  |
| Terminal.error        | 錯誤訊息        | 重新連線     | 連線失敗       | back → 首頁；retry → connecting |
| Terminal.disconnected | 「連線中斷」    | 重新連線     | WS 斷線        | back → 首頁；retry → connecting |

表格的威力在「退出路徑」欄位：**如果這格是空的，這就是一個 UX 死胡同。**

---

## 三個 Mobile App UX 設計原則

從這個案例提煉出的三個原則，適用於所有 mobile app：

### 原則 1：每個畫面的每個狀態都需要退出路徑

沒有例外。即使是「connecting」這種過渡狀態，使用者也可能想取消。iOS 的 HIG 和 Material Design 都要求 modal 畫面提供 dismiss 機制 — 如果使用者進不了某個狀態的下一步（連線失敗、timeout、服務無回應），他至少得能退出。

**反模式**：假設使用者只走 happy path。「connected 之後使用者不會想回首頁」是開發者的假設，不是使用者的需求。

### 原則 2：Gate 必須有 fallback

Gate = 使用者必須通過的關卡（biometric、network、auth）。每個 gate 的設計不只是「成功時怎麼做」，還包含「失敗時的替代路徑」。

| Gate                        | 成功               | 失敗 fallback                           |
| --------------------------- | ------------------ | --------------------------------------- |
| Biometric（Face ID / 指紋） | 讀取憑證、繼續連線 | 密碼 fallback（`biometricOnly: false`） |
| Network（Tailscale VPN）    | WS 連線            | 顯示「網路不可用」+ 重試                |
| Auth（ttyd basic auth）     | 進入終端機         | 顯示「認證失敗」+ 建議重新配對          |

`biometricOnly: true` 就是缺少 fallback 的典型案例 — Face ID 不可用（戴口罩、光線差、指紋模糊）時使用者直接被擋住，沒有替代方案。改為 `biometricOnly: false` 讓系統提供密碼 fallback。

### 原則 3：輸入機制是設計產物，不是實作細節

「手機打字操作 CLI」的輸入設計決策比想像的多：

| 設計決策      | 選項                                               | 取捨                                                               |
| ------------- | -------------------------------------------------- | ------------------------------------------------------------------ |
| Keyboard type | `visiblePassword`（無自動校正）vs `text`（有校正） | CLI 命令不需要自動校正，`visiblePassword` 避免系統「幫忙」修改輸入 |
| Submit model  | Enter 送出整行 vs 逐字元即時送出                   | 整行送出減少網路來回，但沒有即時 tab 補全回饋                      |
| IME policy    | 關閉建議、關閉自動校正、關閉個人化學習             | CLI 輸入內容可能包含密碼和路徑，IME 學習是安全風險                 |
| Special keys  | Esc / Tab / Ctrl 組合鍵                            | 手機鍵盤沒有這些鍵，需要自訂工具列                                 |

這些決策在企劃階段就應該做，因為它們影響 UI layout（是否需要輸入框？工具列放什麼鍵？）和 protocol 設計（逐字元還是整行？）。事後補的 `TextField` 參數列表（`enableSuggestions: false, autocorrect: false, enableIMEPersonalizedLearning: false`）全是散落的 hotfix，不是設計產物。

---

## 系統性方法：從操作盤點到畫面狀態矩陣

操作盤點是 BDD 的起點（使用者做什麼、成功時發生什麼、失敗時發生什麼）。但盤點到「前端引導」就停了 — 它回答了「顯示什麼」但沒回答「能做什麼」「怎麼離開」。

補上的步驟：

1. **從操作盤點列出所有畫面**：每個操作涉及哪些畫面？（首頁 → 配對畫面 → QR 掃描 → 終端機畫面）
2. **每個畫面列出所有狀態**：這個畫面有哪些 enum 值或邏輯分支？
3. **填畫面狀態矩陣**：顯示 / 可用操作 / 進入條件 / 退出路徑。退出路徑欄位為空 = UX 死胡同
4. **每個 gate 標注 fallback**：biometric / network / auth 各有什麼替代方案？
5. **輸入機制列決策表**：keyboard type / submit model / IME policy / special keys

這不是額外的文件負擔 — 是操作盤點本來就該產出的下一層。一張表能在 10 分鐘內暴露所有 UX 死胡同，省掉實機測試才發現的成本。

## 延伸閱讀

本文的觀察和判讀在 [UX Design 畫面設計](/ux-design/) 教學系列中展開為系統性的教學模組：[畫面狀態矩陣的定義與填寫方法](/ux-design/01-screen-state-machine/state-matrix-definition/)、[Gate 分類與三問設計法](/ux-design/02-gate-fallback/gate-three-questions/)、[輸入機制決策表](/ux-design/03-input-mechanism/four-dimension-decision/)。
