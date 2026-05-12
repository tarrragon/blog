---
title: "9.C11 Minecraft Earth：Azure Cosmos DB 上的全球分散式 AR 遊戲"
date: 2026-05-12
description: "Minecraft Earth 用 Cosmos DB 跨地區分散、測試到 100 萬 RU/s 仍維持承諾延遲"
weight: 11
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "azure", "surge"]
---

這個案例的核心責任是說明「全球分散式 multi-model DB」的容量設計取捨。Minecraft Earth 是 AR 手機遊戲（已停運、但案例本身保留）、跟 Pokémon GO 同類負載 — 玩家位置即時更新、跨地區即時互動、預期會在熱門地區 surge。Cosmos DB 的設計回應這類「跨地區 + 多 model」需求。

## 觀察

Minecraft Earth 在 Azure Cosmos DB 的關鍵敘述（引自 [Minecraft Earth and Azure Cosmos DB](https://azure.microsoft.com/en-us/blog/minecraft-earth-and-azure-cosmos-db-part-2-delivering-turnkey-geographic-distribution/)）：

| 指標       | 數字 / 內容                         |
| ---------- | ----------------------------------- |
| 容量測試   | 100 萬 RU/s（Request Units / 秒）   |
| 延遲承諾   | 99 百分位 < 10ms（地區內讀）        |
| 一致性選項 | 5 個一致性層級（strong → eventual） |
| 地理分散   | turnkey global distribution         |
| 可用性 SLA | 99.99%（multi-region 99.999%）      |

Cosmos DB 平台特性（引自 [Cosmos DB technical overview](https://azure.microsoft.com/en-us/blog/a-technical-overview-of-azure-cosmos-db/)）：

- 配置擴容延遲：99 百分位 5 秒內生效
- 多 model 支援：SQL API、MongoDB API、Cassandra API、Gremlin、Table
- partition 動態分裂：透明
- 5 個 well-defined consistency levels（strong / bounded staleness / session / consistent prefix / eventual）

## 判讀

Cosmos DB 設計揭露三個全球 KV / document DB 的容量設計重點。

1. **一致性是 spectrum、不是 binary**：Cosmos DB 提供 5 個層級、每個延遲與吞吐特性不同。AR 遊戲的玩家位置不需要 strong consistency（位置稍微 stale 沒問題）、但庫存交易需要 strong。同一 application 內不同操作選不同 consistency、是進階的容量設計策略。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的一致性取捨。
2. **Request Unit (RU) 是抽象容量單位**：1 RU = 1 KB document 的 strong read 成本、寫成本約 5 RU、複雜 query 可達數百 RU。容量規劃變成「估每個操作多少 RU × 操作頻率」、跟「估 CPU / IOPS」是不同的思維。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的容量單位設計。
3. **turnkey global distribution = 容量單位的全球複製**：開啟跨地區後、容量在每個地區都 mirror 一份、成本乘以地區數。對中等規模團隊、turnkey 省下大量 ops、但要算「全球複製的成本是否值得業務需求」。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。

需要警惕：「100 萬 RU/s 通過測試」是 *壓測通過*、不是 *生產持續跑*。實際營運要看 partition key 設計是否均勻、是否有 hot partition、跨地區複製延遲是否符合業務需求。

## 策略

可重用的工程做法：

1. **一致性需求分流到不同 collection / table**：同一 application 不同操作有不同一致性需求、用不同 collection 配不同 consistency level、不要一刀切。
2. **partition key 設計影響容量上限**：跟 DynamoDB 一樣、hot partition 會讓名義容量達不到。Cosmos DB 的特殊性是「synthetic partition key」可以混合多個 field 強制分散。對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 的 hot partition 識別。
3. **RU-based pricing 鼓勵 query 最佳化**：每個 expensive query 都吃 RU、優化 query 直接降成本。對應 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/) 的持續改進迴圈。

跨平台等效：AWS DynamoDB Global Tables（global KV）、GCP Spanner（global SQL with strong consistency）、ScyllaDB Cloud（自管 Cassandra）都是對等候選。差異是 multi-model 廣度（Cosmos 最廣）vs 一致性深度（Spanner 最強）。

## 下一步路由

- 想設計全球分散 KV → [01 資料庫模組](/backend/01-database/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想對照強一致全球 OLTP → [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)
- 想對照單區 KV 高吞吐 → [9.C5 Amazon Ads DynamoDB](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)
- 想理解 consistency level 的取捨 → [01.5 transaction boundary](/backend/01-database/transaction-boundary/)

## 引用源

- [Minecraft Earth and Azure Cosmos DB part 2: Delivering turnkey geographic distribution](https://azure.microsoft.com/en-us/blog/minecraft-earth-and-azure-cosmos-db-part-2-delivering-turnkey-geographic-distribution/)
- [A technical overview of Azure Cosmos DB](https://azure.microsoft.com/en-us/blog/a-technical-overview-of-azure-cosmos-db/)
- [Azure Cosmos DB: Pushing the frontier of globally distributed databases](https://azure.microsoft.com/en-us/blog/azure-cosmos-db-pushing-the-frontier-of-globally-distributed-databases/)
