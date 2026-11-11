---
title: "Cutover Window"
date: 2026-05-11
description: "說明正式切換發生的觀察窗口、停止條件與回退判讀範圍"
weight: 145
tags: ["backend", "knowledge-card", "migration", "reliability"]
---

Cutover window 的核心概念是「正式切換發生並被密集觀察的時間與條件範圍」。它連接 [cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[migration gate](/backend/knowledge-cards/migration-gate/) 與 [rollback-window](/backend/knowledge-cards/rollback-window/)，讓切換成為一段可停止、可判讀的窗口，脫離瞬間按鈕的思維。

## 跟其他概念的關係

Cutover window 位在 [release gate](/backend/knowledge-cards/release-gate/)、[steady state](/backend/knowledge-cards/steady-state/) 與 [evidence package](/backend/knowledge-cards/evidence-package/) 之間。Release gate 決定能否開始切換，cutover window 定義切換後多久內要看哪些訊號、達到什麼條件才算穩定。

## 可觀察訊號

系統需要 cutover window 的訊號是：

- 新路徑開始承接正式讀取或寫入
- 切換後需要觀察 mismatch、latency、error rate 或 lag
- 回退條件只在切換初期仍然低成本
- 多個入口會分批切換，需要分別記錄時間窗

## 接近真實網路服務的例子

客服後台先切到新 `payment_state` 讀取後，前 30 分鐘是 cutover window。這段期間要看 mismatch sample、客服查詢慢查詢、對帳補償量與 rollback window；穩定後才放行使用者可見讀取。

## 判斷條件與後果

Cutover window 的定義缺項時，切換退回成一次按鈕。沒有記錄開始時間時，多個入口分批切換，各批的訊號對不回各自的時間窗。沒有觀察長度與通過條件時，放行使用者可見讀取的時機由現場的感覺決定。沒有 [stop condition](/backend/knowledge-cards/stop-condition/) 與 owner 時，mismatch 上升也沒有一個值、沒有一個人負責喊停，而回退只在切換初期還是低成本，拖過這段時間之後回退的代價變高。窗口的時間、訊號與放行決定沒有寫進 [evidence package](/backend/knowledge-cards/evidence-package/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 時，事後回放不出切換當時看到了什麼、依據什麼放行。
