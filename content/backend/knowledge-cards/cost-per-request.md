---
title: "Cost Per Request"
date: 2026-05-12
description: "把雲端成本拆到單一 API 請求的 unit economics 模型"
weight: 239
---

Cost per request 的核心概念是「把月帳單 / 總 RPS = 每個請求的成本」、進一步拆到每個 endpoint、每個 stage（app / DB / cache / network）。讓容量決策有 unit economics 邊界。可先對照 [Headroom Budget](/backend/knowledge-cards/headroom-budget/)。

## 跟其他概念的關係

Cost per request 是 FinOps 的最小單位。可以對齊業務 metric：cost per active user、cost per transaction、cost per ML inference。不同 endpoint 成本差很大：登入請求可能 $0.0001、結帳請求可能 $0.001（10x 差距）。可先對照 [Headroom Budget](/backend/knowledge-cards/headroom-budget/)。

## 可觀察訊號與例子

需要算 cost per request 的訊號是「月帳單上升但不知道誰造成的」。對應案例：[Zomato TiDB → DynamoDB 50% 成本降](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 算出每筆計費事件的成本後決定遷移；[Netflix Aurora 28% 成本降](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 層 cost-per-request 量化才能評估 consolidation 價值。

## 判斷條件與後果

Cost per request 的分子漏掉某個 stage 時，算出來的單位成本低於實際，拿它評估遷移或 consolidation 時，會低估被漏掉那一段的份額。分子涵蓋的 stage 是 app compute、DB read/write、cache、network egress 與第三方 API。跨 region egress、監控服務（CloudWatch、Stackdriver、Application Insights）的 metric 費用與 log ingest 費用不會出現在任何一個 endpoint 的成本裡，最常被漏算。這個數字由當月帳單與請求量算出，流量組成或機型改變之後就過期，所以每月重算一次，每季依它做一次 right-sizing。
