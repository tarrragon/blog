---
title: "Migration"
date: 2026-04-23
description: "說明系統如何把資料、流量或結構從舊狀態移到新狀態"
weight: 139
---

Migration 的核心概念是「把系統從舊狀態移到新狀態的受控流程」。它可以是 [schema migration](/backend/knowledge-cards/schema-migration/)、資料 [backfill](/backend/knowledge-cards/backfill/)、服務拆分、平台切換、read path 切換或事件模型改版。常見做法之一是 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 跟其他概念的關係

Migration 是 release、資料一致性與操作風險的交界。它通常需要同時考慮相容性、觀測、回復、[cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[fallback plan](/backend/knowledge-cards/fallback-plan/) 與 [correctness check](/backend/knowledge-cards/correctness-check/)。

## 可觀察訊號與例子

系統需要 migration 設計的訊號是新舊路徑會並存一段時間。電商把搜尋從舊索引切到新索引時，需要 [shadow read](/backend/knowledge-cards/shadow-read/) 比對結果、backfill 既有商品、觀察錯誤率，最後再切正式流量。

## 判斷條件與後果

Migration 在新舊路徑並存的期間，任何一步都可能要停下或回頭，「停在哪裡、怎麼回去」是否事先有答案，決定了出狀況時的代價。沒有回復條件與完成標準時，遷移做到一半出狀況，團隊當下才討論要回頭還是繼續，而舊路徑可能已經拆掉；沒有擁有者、資料範圍與驗證方式時，哪些資料已經搬過、搬得對不對、誰能決定切換，要事後拼湊。資料變更、application release 與流量切換綁在同一次部署時，出錯之後分不出是哪一步造成的，回復也只能三者一起回；拆成可觀察、可停止的步驟時，步驟之間各有一個 [Migration Gate](/backend/knowledge-cards/migration-gate/) 可以停下。高風險的 migration 上線前沒有做過 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/) 時，回復程序第一次執行就是在事故當下。
