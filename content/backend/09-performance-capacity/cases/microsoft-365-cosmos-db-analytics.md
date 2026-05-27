---
title: "9.C30 Microsoft 365：從 MongoDB 遷移到 Cosmos DB 的分析平台"
date: 2026-05-12
description: "Microsoft 365 把使用分析平台從 MongoDB 遷移到 Cosmos DB、planet-scale 全球分散式分析"
weight: 30
tags: ["backend", "performance", "capacity", "case-study", "data-architecture", "azure", "sustained-growth"]
---

這個案例的核心責任是填補 Azure data-architecture 維度缺口、並提供「MongoDB → Cosmos DB」這個跨產品遷移的官方範本。Microsoft 365 是全球最大 SaaS 之一（月活十億級）、其使用分析平台的容量需求是 planet-scale。

## 觀察

Microsoft 365 在 Cosmos DB 的關鍵敘述（引自 [Microsoft 365 boosts usage analytics with Azure Cosmos DB](https://azure.microsoft.com/en-us/blog/microsoft-365-boosts-usage-analytics-with-azure-cosmos-db/)）：

| 指標     | 內容                                                                             |
| -------- | -------------------------------------------------------------------------------- |
| 用戶規模 | Microsoft 365 全球用戶（十億級 MAU）                                             |
| 工作負載 | 使用分析（usage analytics）                                                      |
| 遷出技術 | MongoDB                                                                          |
| 遷入技術 | Azure Cosmos DB                                                                  |
| 遷移動機 | 「globally-distributed, multi-model」「virtually unlimited elastic scalability」 |

關鍵敘述：「The team decided to replace MongoDB with Azure Cosmos DB, a fully managed globally-distributed, multi-model database service designed for global distribution and virtually unlimited elastic scalability.」

## 判讀

Microsoft 365 案例揭露三個全球 SaaS 分析平台的工程重點。

1. **MongoDB → Cosmos DB 是「相容 API + 升級擴展性」的遷移路徑**：Cosmos DB 提供 MongoDB API 相容、應用層程式幾乎不用改、但底層儲存改用 Cosmos DB 的分散式架構。這層遷移成本遠低於改寫 application 到 native Cosmos DB SQL API、適合大規模既有系統。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)、跟 [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) 形成對照。
2. **分析平台 vs 交易平台的 DB 取捨不同**：交易平台優先 latency + consistency（[9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)）、分析平台優先 throughput + global distribution + cost。Cosmos DB 5 個 consistency level 讓分析場景可以選 weakest（eventual / session），換最大 throughput。對應 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) 同思維。
3. **Microsoft 自家產品 dogfood Cosmos DB**：跟 Amazon Prime Day 用自家 DynamoDB（[9.C1](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)）、Google 自家用 Spanner（[9.C10](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)）一樣 — 雲商旗艦 DB 都會用在自家旗艦產品。讀此類 dogfood 案例的權重應該高、因為「雲商自己賭身家」。

需要警惕：

- 案例 *沒有* 提具體 throughput、latency、cost 數字。Microsoft 內部數字通常不公開、跟 AWS / GCP 案例的數字密度差很多。
- 「MongoDB 不夠用」是行銷話術。實際是 *MongoDB 在某些 workload pattern 下不夠用*、不是普遍結論。

## 策略

可重用的工程做法：

1. **MongoDB-compatible Cosmos DB 是大規模遷移的捷徑**：應用層改動少、底層擴展性升級。但要驗證 *特定 query pattern* 在兩邊行為一致。對應 [01.3 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 的 dual-write 驗證。
2. **分析平台用 weakest acceptable consistency**：session consistency 或 eventual consistency 通常夠用、能換到 3-10x throughput。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的一致性取捨。
3. **dogfood 是 vendor selection 的重要訊號**：vendor 自家是否用在 production-critical workload、能告訴你「他們對自己服務的信任度」。
4. **Multi-model 是 Cosmos DB 的差異化價值**：同一個服務可以用 SQL API / MongoDB API / Cassandra API / Gremlin / Table API、避免多個 DB 服務並存。

跨平台等效：AWS DynamoDB（KV）+ DocumentDB（MongoDB-compatible）、GCP Firestore（document）+ Spanner（SQL）+ Bigtable（KV）— 各家用不同產品覆蓋 multi-model、Cosmos DB 是少數「單一產品支援多 model」。

## 下一步路由

- 對照其他 Cosmos DB 案例 → [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) / [9.C21 ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)
- 對照其他 dogfood 案例 → [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)
- 想做 MongoDB-compatible 遷移 → [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)
- 想理解 multi-model 取捨 → [01 資料庫模組](/backend/01-database/) + [00 服務選型模組](/backend/00-service-selection/)
- 想對比 Cosmos DB MongoDB API vs SQL API 的選型 → [Cosmos DB MongoDB API vs SQL API](/backend/01-database/vendors/cosmosdb/mongodb-api-vs-sql-api/)
- 想做 RU 成本模型與容量 sizing → [Cosmos DB RU 成本模型](/backend/01-database/vendors/cosmosdb/ru-cost-model-sizing/)

## 引用源

- [Microsoft 365 boosts usage analytics with Azure Cosmos DB](https://azure.microsoft.com/en-us/blog/microsoft-365-boosts-usage-analytics-with-azure-cosmos-db/)
- [A technical overview of Azure Cosmos DB](https://azure.microsoft.com/en-us/blog/a-technical-overview-of-azure-cosmos-db/)
