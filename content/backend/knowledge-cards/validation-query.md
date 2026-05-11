---
title: "Validation Query"
date: 2026-05-11
description: "說明遷移、回填與修復期間如何用查詢證明資料語意是否一致"
weight: 141
tags: ["backend", "knowledge-card", "database", "migration"]
---

Validation query 的核心概念是「用可重跑查詢證明資料語意是否符合遷移規則」。它連接 [correctness check](/backend/knowledge-cards/correctness-check/)、[backfill](/backend/knowledge-cards/backfill/) 與 [migration gate](/backend/knowledge-cards/migration-gate/)，讓資料變更不只靠 job log 或人工抽樣判斷。

## 概念位置

Validation query 位在 [schema migration](/backend/knowledge-cards/schema-migration/)、[data reconciliation](/backend/knowledge-cards/data-reconciliation/) 與 [evidence package](/backend/knowledge-cards/evidence-package/) 之間。Correctness check 定義要驗什麼，validation query 則把規則落成可查、可保存、可交接的證據。

## 可觀察訊號

系統需要 validation query 的訊號是：

- 新舊欄位或新舊資料模型會並存一段時間
- backfill job 顯示完成，但仍需要證明資料語意正確
- cutover 前要知道 mismatch 集中在哪些資料範圍
- 事故修復後要留下可回放的資料證據

## 接近真實網路服務的例子

訂單服務把 `status` 裡的付款語意拆到 `payment_state` 時，validation query 可以比對每批訂單的新舊語意、缺值筆數、mismatch sample 與 replication lag 對位。這些結果會進入 release gate，而不是只停在 migration job 的成功訊息。

## 設計責任

Validation query 要保留 query version、time range、資料範圍、mismatch 分類與 owner。它的目標是支援 [rollback window](/backend/knowledge-cards/rollback-window/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 判讀，讓團隊能知道下一步是繼續、暫停、回退讀取，還是做資料修補。
