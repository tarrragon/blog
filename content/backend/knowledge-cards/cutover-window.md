---
title: "Cutover Window"
date: 2026-05-11
description: "說明正式切換發生的觀察窗口、停止條件與回退判讀範圍"
weight: 144
tags: ["backend", "knowledge-card", "migration", "reliability"]
---

Cutover window 的核心概念是「正式切換發生並被密集觀察的時間與條件範圍」。它連接 [cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[migration gate](/backend/knowledge-cards/migration-gate/) 與 [rollback-window](/backend/knowledge-cards/rollback-window/)，讓切換不是一個瞬間按鈕，而是一段可停止、可判讀的窗口。

## 概念位置

Cutover window 位在 [release gate](/backend/knowledge-cards/release-gate/)、[steady state](/backend/knowledge-cards/steady-state/) 與 [evidence package](/backend/knowledge-cards/evidence-package/) 之間。Release gate 決定能否開始切換，cutover window 定義切換後多久內要看哪些訊號、達到什麼條件才算穩定。

## 可觀察訊號

系統需要 cutover window 的訊號是：

- 新路徑開始承接正式讀取或寫入
- 切換後需要觀察 mismatch、latency、error rate 或 lag
- 回退條件只在切換初期仍然低成本
- 多個入口會分批切換，需要分別記錄時間窗

## 接近真實網路服務的例子

客服後台先切到新 `payment_state` 讀取後，前 30 分鐘是 cutover window。這段期間要看 mismatch sample、客服查詢慢查詢、對帳補償量與 rollback window；穩定後才放行使用者可見讀取。

## 設計責任

Cutover window 要定義開始時間、觀察長度、通過條件、[stop condition](/backend/knowledge-cards/stop-condition/) 與 owner。它應進入 [evidence package](/backend/knowledge-cards/evidence-package/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/)，讓事後能回放切換當時的訊號。
