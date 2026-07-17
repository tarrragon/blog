---
title: "模組四：錯誤狀態與回復"
date: 2026-06-19
description: "錯誤不只是紅色文字 — 是一個需要設計退出路徑的狀態"
weight: 4
tags: ["ux-design", "error", "recovery", "retry"]
---

回答「出錯時使用者能做什麼」。

## 章節

- [錯誤訊息撰寫原則](/ux-design/04-error-recovery/error-message-principles/) — 使用者能讀懂發生什麼、能決定下一步做什麼
- [Retry 機制 UX](/ux-design/04-error-recovery/retry-mechanism-ux/) — 自動 vs 手動重試、指數退避 vs 立即重試的策略選擇
- [Degraded mode 設計](/ux-design/04-error-recovery/degraded-mode-design/) — 部分功能不可用時的告知策略，靜默隱藏 vs 明確標示 vs 替代方案
- [error → retry → error 循環的逃生口設計](/ux-design/04-error-recovery/error-loop-escape/) — 重試持續失敗時，使用者需要第二條路離開失敗循環

## 跨分類引用

- ← [ux-design 模組一](/ux-design/01-screen-state-machine/)：error 狀態在狀態矩陣中的退出路徑
- → [ux-design 模組六](/ux-design/06-interaction-feedback/)：錯誤是三層回饋的「結果通知」之一；重試按鈕的 loading 狀態與等待指示設計
- → [testing 模組一](/testing/01-test-strategy-layers/)：error 回復路徑需要 widget test 覆蓋
- → [monitoring 模組一](/monitoring/01-mental-model/)：error 事件是四類事件之一
