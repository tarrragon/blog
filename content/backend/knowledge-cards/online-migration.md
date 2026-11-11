---
title: "Online Migration"
date: 2026-04-23
description: "說明服務持續接流量時如何完成資料或 schema 遷移"
weight: 77
---

Online migration 的核心概念是「在服務持續運作期間完成資料或 schema 遷移」。它讓系統在不中斷主要服務的情況下搬移資料、改欄位、換儲存或調整索引。 可先對照 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 跟其他概念的關係

Online migration 是 release、database、observability 與 rollback 的共同工程。它通常搭配 [Expand / Contract](/backend/knowledge-cards/expand-contract/)、backfill、dual write、shadow read、cutover 與 correctness check。

## 可觀察訊號與例子

系統需要 online migration 的訊號是資料量大、停機代價高或 rolling update 期間新舊版本會共存。把會員資料從舊 table 搬到新 table 時，服務仍要能註冊、登入與更新會員資料。

## 判斷條件與後果

Online migration 的每個階段（backfill、dual write、shadow read、cutover）都在服務運作中改動資料，判斷的對象是某一階段出錯時，系統停在什麼狀態。沒有資料比對與監控時，backfill 寫錯的資料跟正常寫入混在一起，到 cutover 之後才被讀到，而那時舊路徑已經停用；沒有速率限制時，backfill 與線上寫入搶同一個資料庫，註冊、登入這類請求因為遷移而變慢；沒有停止條件與回滾時，某一階段的指標變差也沒有依據停下，只剩往前推或在事故中臨時拆解兩條路。這些代價都由線上使用者承擔，所以每個階段要能單獨驗證，並保留回到前一階段的路徑。
