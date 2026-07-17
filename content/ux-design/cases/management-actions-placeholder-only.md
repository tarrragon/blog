---
title: "U.C20 管理模式操作全是佔位 — dev toast 讓未接線看起來有反應"
date: 2026-07-17
description: "UI 有按鈕、domain 層功能也寫完、按下去只有開發提示或 log：佔位 handler 比沒有按鈕更糟 — 按鈕的存在承諾功能存在，dev toast 讓開發自測「有反應」、掩蓋未接線"
weight: 20
tags: ["ux-design", "case-study", "interaction-feedback", "placeholder", "technical-debt", "flutter", "mobile"]
---

書庫管理 app 的管理模式有完整的批次操作 domain 服務、畫面上也有一整排批次操作按鈕 — 兩者之間的接線全數是佔位。佔位 handler 的風險是雙重的：對使用者，可點的假按鈕比沒有按鈕更糟（按鈕的存在承諾功能存在）；對開發者，接了 dev toast / log 的佔位在自測時「有反應」，讓未接線在驗收前不可見。

## 觀察

驗收回報「右下按鈕按了沒反應」；管理模式批次操作 UI 的盤點結果：

| UI 元件                          | onPressed 實際行為             | 位置                                    |
| -------------------------------- | ------------------------------ | --------------------------------------- |
| 右下浮動按鈕 FAB（「批次操作」） | 只彈開發用的點擊事件測試 toast | `library_display_extensions.dart:62-66` |
| 底部欄「編輯」「分享」「刪除」   | 只寫 log「...尚未實作」        | `library_display_page.dart:129,144,159` |
| AppBar「更多選項」               | 只寫 log「尚未實作」           | `library_display_page.dart:63-67`       |

對照規格（SPEC-006 FR-9 / FR-10）：批次操作的 domain 層已完整實作 — `LibraryManagementService.performBatchOperation`（刪除 / 改來源 / 改重要度 / 增刪標籤）與 Command 模式的編輯服務（undo / redo）都在 — **是 UI 到 service 的最後一段接線沒做**。團隊已有「佔位實作」的追蹤票（佔位掃描盲區改善），本案是同類技術債在管理模式的集中呈現。

附帶：底部欄只在「已選取至少一本」時才出現 — 驗收者若沒先勾書、連佔位的編輯 / 分享 / 刪除鍵都看不到。

## 判讀

1. **可點的假按鈕是負資產**。按鈕存在 = 系統承諾功能存在，點了沒反應被讀成「壞掉」（體感同 U.C5 零回饋）— 對產品信任的傷害大於「功能還沒有」。未完成的功能在 UI 上的正確形態是隱藏、或 disabled + 說明（「即將推出」），不是可點的佔位。

2. **dev toast 佔位掩蓋未接線**。接了 toast 的按鈕在開發自測時「有反應」— 開發回饋（toast 彈了）與使用者回饋（操作確實執行）被混為一談，佔位從此不在任何人的視野裡，直到驗收。log-only 佔位更隱形：畫面上完全無反應。

3. **domain 完成 + UI 佔位 = 完成度斷層**。規格對照表寫「批次管理操作：已實作」指的是 service 層 — 進度報告以 domain 層為準時，UI 未接線的斷層不會出現在任何狀態欄位上，驗收是唯一暴露點。完成度要分層記帳（domain / UI 接線 / 驗收通過）。

## 策略

1. **佔位 handler 用統一可掃描的標記**（固定的 dev-placeholder helper 或註解格式），release 前用 grep 掃描清零或轉成 disabled + 說明。

2. **未接線功能的 UI 三選一**：隱藏（功能不該被發現）、disabled + 原因（讓使用者知道存在但未開放）、接線（完成它）— 可點無反應不在選項裡。

3. **完成度分層記帳**：domain 完成、UI 接線、驗收通過是三個獨立狀態 — 「已實作」要標明層級，避免 UI 斷層藏在 domain 的完成宣告後面。

## 下一步路由

- 零回饋按鈕的原型案例 → [U.C5 匯出按鈕零回饋](/ux-design/cases/export-button-zero-feedback/)
- 回饋鏈路的其他斷點 → [U.C9 提取成功卻誤報失敗](/ux-design/cases/async-listener-false-failure/)、[U.C19 計數被版面擠壓](/ux-design/cases/selection-count-layout-starvation/)
- 三層回饋的完整要求 → [互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)
