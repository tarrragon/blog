---
title: "Cost Per Request"
date: 2026-05-12
description: "把雲端成本拆到單一 API 請求的 unit economics 模型"
weight: 238
---

Cost per request 的核心概念是「把月帳單 / 總 RPS = 每個請求的成本」、進一步拆到每個 endpoint、每個 stage（app / DB / cache / network）。讓容量決策有 unit economics 邊界。可先對照 [Headroom Budget](/backend/knowledge-cards/headroom-budget/)。

## 概念位置

Cost per request 是 FinOps 的最小單位。可以對齊業務 metric：cost per active user、cost per transaction、cost per ML inference。不同 endpoint 成本差很大：登入請求可能 $0.0001、結帳請求可能 $0.001（10x 差距）。可先對照 [Headroom Budget](/backend/knowledge-cards/headroom-budget/)。

## 可觀察訊號與例子

需要算 cost per request 的訊號是「月帳單上升但不知道誰造成的」。對應案例：[Zomato TiDB → DynamoDB 50% 成本降](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 算出每筆計費事件的成本後決定遷移；[Netflix Aurora 28% 成本降](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 層 cost-per-request 量化才能評估 consolidation 價值。

## 設計責任

Cost per request 必須包含 *所有 stage*：app compute、DB read/write、cache、network egress、第三方 API。常見漏算：跨 region egress、CloudWatch / Stackdriver / Application Insights metric 成本、log ingest 成本。每月 review、每季 right-sizing。
