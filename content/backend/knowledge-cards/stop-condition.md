---
title: "Stop Condition"
date: 2026-05-11
description: "說明變更、實驗或事故處理何時必須暫停、回退或改路線"
weight: 159
tags: ["backend", "knowledge-card", "reliability", "incident-response"]
---

Stop condition 的核心概念是「事前定義何時必須暫停、回退或改路線」。它連接 [release gate](/backend/knowledge-cards/release-gate/)、[rollback strategy](/backend/knowledge-cards/rollback-strategy/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/)，避免團隊在壓力下用感覺決定是否繼續。

## 跟其他概念的關係

Stop condition 位在 [migration gate](/backend/knowledge-cards/migration-gate/)、[cutover-window](/backend/knowledge-cards/cutover-window/) 與 [steady state](/backend/knowledge-cards/steady-state/) 之間。Gate 說明能否開始，stop condition 說明開始後看到哪些訊號必須停。

## 可觀察訊號

系統需要 stop condition 的訊號是：

- rollout、backfill、replay 或 experiment 會逐批擴大影響
- 指標短暫變壞時需要知道是觀察、暫停還是回退
- owner 需要在事故現場快速做一致決策
- post-incident review 要檢查當時是否該更早停下來

## 接近真實網路服務的例子

資料庫 migration 可以定義 `mismatch_rate >= 0.1% for two consecutive batches` 或 `replication_lag >= 30s for 10 minutes` 作為 stop condition。達到條件時，團隊先暫停下一批 backfill 或回到 fallback read，而不是等使用者回報。

## 判斷條件與後果

Stop condition 由訊號、門檻、觀察窗口、對應動作與 owner 組成，任一項缺席時，現場是否停下又回到當下的感覺：只有訊號沒有門檻，指標變差多少算該停沒有共識；沒有觀察窗口，短暫的抖動與持續的惡化分不開，前者讓 rollout 被誤停，後者被當成抖動放過（`for two consecutive batches` 就是窗口）；沒有對應動作，觸發之後是暫停、回退還是改路線要臨場決定；沒有 owner，條件觸發了也沒有人有權執行。Stop condition 寫進 [release gate](/backend/knowledge-cards/release-gate/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 時，事後復盤對照得到「當時是否該更早停」；門檻的依據（基準值、過去的事故數據）收進 [evidence package](/backend/knowledge-cards/evidence-package/) 時，門檻被質疑時拿得出它從哪裡來。
