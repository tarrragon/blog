---
title: "Online Migration"
date: 2026-04-23
description: "說明服務持續接流量時如何完成資料或 schema 遷移"
weight: 76
---


Online migration 的核心概念是「在服務持續運作期間完成資料或 schema 遷移」。它讓系統在不中斷主要服務的情況下搬移資料、改欄位、換儲存或調整索引。 可先對照 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 概念位置

Online migration 是 release、database、observability 與 rollback 的共同工程。它通常搭配 [Expand / Contract](/backend/knowledge-cards/expand-contract/)、backfill、dual write、shadow read、cutover 與 correctness check。

## 可觀察訊號與例子

系統需要 online migration 的訊號是資料量大、停機代價高或 rolling update 期間新舊版本會共存。把會員資料從舊 table 搬到新 table 時，服務仍要能註冊、登入與更新會員資料。

## 設計責任

Online migration 要設計階段、監控、速率限制、回滾、資料比對與停止條件。每個階段都要能獨立驗證，並保留回到前一階段的路徑。
