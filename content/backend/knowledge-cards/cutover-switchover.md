---
title: "Cutover / Switchover"
date: 2026-04-23
description: "說明遷移期間如何把正式流量切到新路徑"
weight: 77
---


Cutover / switchover 的核心概念是「把正式讀寫從舊路徑切到新路徑」。它是 migration 中風險最高的時刻，因為使用者流量開始依賴新資料、新服務或新設定。 可先對照 [Dashboard](/backend/knowledge-cards/dashboard/)。

## 概念位置

Cutover 連接資料正確性、部署、觀測與 rollback。切換可以一次完成，也可以用 feature flag、百分比流量、tenant 分批或讀寫分離逐步進行。 可先對照 [Dashboard](/backend/knowledge-cards/dashboard/)。

## 可觀察訊號與例子

系統需要 cutover 計畫的訊號是新舊系統都已準備好，但正式流量尚未切換。把搜尋索引換到新 cluster 時，可以先 shadow read 比對結果，再分批把讀取流量切過去。

## 設計責任

Cutover runbook 要包含前置檢查、切換步驟、觀測指標、停止條件、rollback 條件與負責人。切換後要持續監控錯誤率、延遲、資料差異與使用者回報。
