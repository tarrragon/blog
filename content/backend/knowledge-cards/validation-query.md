---
title: "Validation Query"
date: 2026-05-11
description: "說明遷移、回填與修復期間如何用查詢證明資料語意是否一致"
weight: 142
tags: ["backend", "knowledge-card", "database", "migration"]
---

Validation query 的核心概念是「用可重跑查詢證明資料語意是否符合遷移規則」。它連接 [correctness check](/backend/knowledge-cards/correctness-check/)、[backfill](/backend/knowledge-cards/backfill/) 與 [migration gate](/backend/knowledge-cards/migration-gate/)，讓資料變更不只靠 job log 或人工抽樣判斷。

## 跟其他概念的關係

Validation query 位在 [schema migration](/backend/knowledge-cards/schema-migration/)、[data reconciliation](/backend/knowledge-cards/data-reconciliation/) 與 [evidence package](/backend/knowledge-cards/evidence-package/) 之間。Correctness check 定義要驗什麼，validation query 則把規則落成可查、可保存、可交接的證據。

## 可觀察訊號

系統需要 validation query 的訊號是：

- 新舊欄位或新舊資料模型會並存一段時間
- backfill job 顯示完成，但仍需要證明資料語意正確
- cutover 前要知道 mismatch 集中在哪些資料範圍
- 事故修復後要留下可回放的資料證據

## 接近真實網路服務的例子

訂單服務把 `status` 裡的付款語意拆到 `payment_state` 時，validation query 可以比對每批訂單的新舊語意、缺值筆數、mismatch sample 與 replication lag 對位。這些結果會進入 release gate，而不是只停在 migration job 的成功訊息。

## 判斷條件與後果

Validation query 的結果用來決定下一步是繼續、暫停、回退讀取還是做資料修補，每次執行留下的欄位各自提供這個決定需要的一項資訊。沒有 query version 時，規則改過之後新舊結果無法比較，分不出 mismatch 減少是資料修好了還是查詢改了；沒有 time range 與資料範圍時，看不出 mismatch 集中在哪一批資料，回退讀取只能整批做；沒有 mismatch 分類時，缺值、語意不一致與 replication lag 造成的暫時差異混在同一個數字裡，[rollback window](/backend/knowledge-cards/rollback-window/) 結束前判斷不出是否該停；沒有 owner 時，結果記進 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之後沒有人接著做決定。
