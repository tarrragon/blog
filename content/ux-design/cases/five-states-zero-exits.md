---
title: "U.C1 Terminal 畫面五個狀態零個退出路徑"
date: 2026-06-19
description: "Flutter app 的 Terminal 畫面有 idle/connecting/connected/error/disconnected 五個 enum 狀態，每個狀態都沒有 back 或 disconnect 按鈕 — 使用者一旦進入就出不去"
weight: 1
tags: ["ux-design", "case-study", "navigation", "state-machine", "flutter", "mobile"]
---

這個案例的核心責任是說明「每個畫面每個狀態都需要退出路徑」這個原則為什麼容易在企劃階段被遺漏，以及用什麼工具能系統性地捕捉這類缺口。

## 觀察

app_tunnel 的 Terminal 畫面用一個 `TerminalScreenUiState` enum 管理五個狀態。實機測試前，五個狀態的 UI 實作如下：

| 狀態         | 顯示                   | 可用操作     | 退出路徑 |
| ------------ | ---------------------- | ------------ | -------- |
| idle         | 空白（自動連線）       | 無           | 無       |
| connecting   | 進度指示               | 無           | 無       |
| connected    | 終端機 + 工具列        | 打字、特殊鍵 | 無       |
| error        | 錯誤訊息 + 重連按鈕    | 重新連線     | 無       |
| disconnected | 「連線中斷」+ 重連按鈕 | 重新連線     | 無       |

使用者從首頁點 Connect Terminal 進入後，無論處於哪個狀態都無法返回首頁。唯一退出方式是殺掉 app。

W2-001 修復後加入 back 按鈕的狀態：error、disconnected、connecting。但 idle 和 connected 仍缺退出路徑。

## 判讀

1. **企劃文件的「前端引導」欄位只描述顯示，不描述操作和退出**。操作盤點表的「前端引導」欄位寫了「連線失敗顯示無法連線」— 覆蓋了 error 狀態的顯示，但沒回答「能做什麼」和「怎麼離開」。從 BDD 操作盤點到 UI 實作之間，缺少把「情境」展開成「畫面 × 狀態 × 操作 × 退出」矩陣的步驟。

2. **開發者假設使用者只走 happy path**。「connected 後使用者不會想回首頁」是開發者的隱性假設。實際上使用者可能想：切換到配對畫面重新配對、暫時離開終端機做其他事、遇到問題想重新開始。

3. **error 和 disconnected 有重連按鈕但沒有 back，也是半成品**。重連失敗時使用者被困在 error → retry → error 的循環裡。加 back 按鈕讓使用者有第二條路。

## 策略

1. **畫面狀態矩陣作為設計產物**：把每個畫面的每個狀態展開成四欄表格（顯示 / 可用操作 / 進入條件 / 退出路徑）。退出路徑欄位為空 = UX 死胡同，10 分鐘能查完所有畫面。

2. **退出路徑是預設要求**：每個畫面的每個狀態至少要有一條退出路徑。即使是 connecting 這種過渡狀態，使用者也應該能取消。這跟 iOS HIG 和 Material Design 對 modal 畫面的 dismiss 要求一致。

3. **Widget test 覆蓋退出路徑**：狀態矩陣直接轉成 test case — 每個狀態找到 back 按鈕、tap、斷言導航到首頁。

## 下一步路由

- 想用狀態矩陣設計畫面 → [畫面狀態矩陣的定義與填寫方法](/ux-design/01-screen-state-machine/state-matrix-definition/)
- 連線類流程每個狀態的回饋與退出路徑 → [互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)的畫面級回饋段
- 想建 widget test 覆蓋導航 → [模組四：自動化 UI 驗證](/testing/04-ui-automation/)
- 類似案例（Gate fallback）→ [U.C2 biometricOnly 無 fallback](/ux-design/cases/biometric-only-no-fallback/)
