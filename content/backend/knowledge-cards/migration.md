---
title: "Migration"
date: 2026-04-23
description: "說明系統如何把資料、流量或結構從舊狀態移到新狀態"
weight: 138
---


Migration 的核心概念是「把系統從舊狀態移到新狀態的受控流程」。它可以是 [schema migration](/backend/knowledge-cards/schema-migration/)、資料 [backfill](/backend/knowledge-cards/backfill/)、服務拆分、平台切換、read path 切換或事件模型改版。常見做法之一是 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 概念位置

Migration 是 release、資料一致性與操作風險的交界。它通常需要同時考慮相容性、觀測、回復、[cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[fallback plan](/backend/knowledge-cards/fallback-plan/) 與 [correctness check](/backend/knowledge-cards/correctness-check/)。

## 可觀察訊號與例子

系統需要 migration 設計的訊號是新舊路徑會並存一段時間。電商把搜尋從舊索引切到新索引時，需要 [shadow read](/backend/knowledge-cards/shadow-read/) 比對結果、backfill 既有商品、觀察錯誤率，最後再切正式流量。

## 設計責任

Migration 要定義階段、擁有者、資料範圍、驗證方式、回復條件與完成標準。高風險 migration 應把資料變更、application release 與流量切換拆成可觀察、可停止的步驟，並在上線前安排 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/) 與 [Migration Gate](/backend/knowledge-cards/migration-gate/)。
