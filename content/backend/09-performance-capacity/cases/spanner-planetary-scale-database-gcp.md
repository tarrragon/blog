---
title: "9.C10 Cloud Spanner：每秒 10 億請求的全球一致性資料庫"
date: 2026-05-12
description: "Google Cloud Spanner 內部峰值 10 億 req/sec、跨地區強一致 — 全球分散式 OLTP 容量參考"
weight: 10
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "gcp", "low-latency-sustained"]
---

這個案例的核心責任是提供「全球一致性 OLTP」的容量參考點。Spanner 是 Google 內部支撐 Ads、Play、Cloud Search 等服務的核心 DB、後來開放為 GCP 服務、是少數公開能撐每秒 10 億請求且維持強一致性的 OLTP 資料庫。

## 觀察

Spanner 公開數字（引自 [Spanner overview](https://cloud.google.com/spanner) / [Spanner performance docs](https://cloud.google.com/spanner/docs/performance)）：

| 指標                  | 數字                                                 |
| --------------------- | ---------------------------------------------------- |
| 內部峰值              | > 10 億 requests / 秒                                |
| Spanner Omni 區域峰值 | 數百萬 QPS、PB 級資料量                              |
| 線性擴展性            | 2 nodes → 45000 reads/sec、4 nodes → 90000 reads/sec |
| 一致性模型            | external consistency（強一致 + 線性化）              |

代表性客戶：Google 內部所有支付、廣告計費、Play 商店、Search 索引；公開客戶包括 Blockchain.com、Niantic（部分服務）、Sharechat、ZEE5、Wayfair。

關鍵設計：TrueTime API（GPS + 原子鐘）讓跨地區交易能維持 external consistency、不是 eventual。

## 判讀

Spanner 案例最值得讀的不是「能撐多大」、是「為什麼要這樣設計才能撐」。

1. **線性擴展是 OLTP 的最高設計目標**：「2 nodes → 45K reads/sec、4 nodes → 90K reads/sec」這個 linear scaling 在傳統 OLTP（PostgreSQL、MySQL）做不到 — 因為 *跨節點交易* 需要 coordinator、coordinator 是 bottleneck。Spanner 用 Paxos + TrueTime 把 coordinator 變成「拓樸感知的多 leader」、才達成線性。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的設計取捨。
2. **強一致 vs 全球部署不是必須二選**：CAP 定理常被解讀為「全球部署只能 eventual consistency」、Spanner 顯示「投入專屬硬體（GPS、原子鐘）+ 演算法（TrueTime）可以同時拿到 strong consistency + global distribution」。但這套硬體投資對其他 vendor 不容易複製。對應 [01 資料庫模組](/backend/01-database/) 的全球 OLTP 選項。
3. **計費粒度 = 容量規劃顆粒**：Spanner 早期最小單位是 100 processing units（pu）≈ 1 node、太大讓中小負載難以用。後來推出 100 pu 起跳的 granular sizing、讓容量規劃可以從小開始。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的容量單位選擇。

需要警惕：「10 億 req/sec」是 Google 內部的某個峰值瞬間、是 Spanner 服務 *全部使用者加總*、不是單一 instance 數字。讀案例時要區分「全球聚合峰值」跟「單一客戶能拿到的最大配額」。

## 策略

可重用的工程做法：

1. **跨地區一致性需求要在設計初期決定**：如果業務必需 strong consistency（金融、ticketing）、選 Spanner 等對等服務；如果 eventual 可接受（社群、推薦）、選 Cassandra / DynamoDB Global Tables 等更便宜的選項。對應 [00 服務選型模組](/backend/00-service-selection/) 的全球一致性需求識別。
2. **節點數即容量單位、預先規劃 sizing**：Spanner 容量 = 節點數 × 單節點 QPS。每年 capacity review 主要在調節點數、不在調 schema。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/)。
3. **跨地區 latency 是強一致的代價**：external consistency 必須等多區 quorum、跨洲交易延遲可達 100-200ms。延遲敏感型業務不能用跨地區 strong consistency。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 latency budget 反推。

跨平台等效：AWS Aurora DSQL（2024 推出、跨地區 strong consistency）、CockroachDB（自管）、TiDB（自管或 cloud）都是對等候選。差異是 TrueTime / 同等同步機制的成熟度。

## 下一步路由

- 想評估全球一致性需求 → [00 服務選型模組](/backend/00-service-selection/) + [01.5 transaction boundary](/backend/01-database/transaction-boundary/)
- 想規劃 OLTP 容量 → [9.6 容量規劃模型](/backend/09-performance-capacity/) + [01 資料庫模組](/backend/01-database/)
- 想對照其他 OLTP 案例 → [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)
- 想看不需要強一致的全球 KV → [9.C11 Minecraft Earth Cosmos DB](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)
- 想理解 TrueTime ε 與外部一致性實作 → [Spanner TrueTime API 深入](/backend/01-database/vendors/spanner/truetime-api-depth/)
- 想對照 Spanner / Aurora DSQL / CockroachDB 不同一致性層 → [Spanner 一致性模型對照](/backend/01-database/vendors/spanner/consistency-models-comparison/)

## 引用源

- [Spanner: Always-on, virtually unlimited scale database](https://cloud.google.com/spanner)
- [Spanner Performance overview](https://cloud.google.com/spanner/docs/performance)
- [Using Cloud Spanner to handle high throughput writes](https://cloud.google.com/blog/products/databases/using-cloud-spanner-to-handle-high-throughput-writes/)
- [Get more out of Spanner with granular instance sizing](https://cloud.google.com/blog/products/databases/get-more-out-of-spanner-with-granular-instance-sizing)
- [Amazon Aurora DSQL for global-scale financial transactions](https://aws.amazon.com/blogs/database/amazon-aurora-dsql-for-global-scale-financial-transactions/)
