---
title: "9.C19 Capcom：Resident Evil / Monster Hunter 在 DynamoDB + EKS 上的遊戲後端"
date: 2026-05-12
description: "Capcom 把 Resident Evil、Street Fighter、Monster Hunter 遊戲後端跑在 DynamoDB + EKS、單一秒位數延遲、營運成本降 30%"
weight: 19
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "sustained-growth"]
---

這個案例的核心責任是說明「遊戲後端 KV」跟「廣告 KV」「電商 KV」的業務語意差異。遊戲後端的 KV 工作負載特性是：玩家狀態（角色、裝備、戰績）必須次秒讀寫、跨 region 同步、防作弊 — 這層需求跟 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的「廣告量測」或 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) 的「AR 玩家位置」都不同。

## 觀察

Capcom 在 AWS 的關鍵敘述（引自 [Capcom Case Study](https://aws.amazon.com/solutions/case-studies/capcom/) 與 [DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)）：

| 指標           | 數字                                          |
| -------------- | --------------------------------------------- |
| 遊戲 IP        | Resident Evil、Street Fighter、Monster Hunter |
| 後端請求量     | billions of requests                          |
| 響應時間       | single-digit millisecond                      |
| 營運成本下降   | 30%                                           |
| 服務組合       | Amazon DynamoDB + Amazon EKS                  |
| 工程資源再配置 | 從 DB 運維轉到遊戲品質與開發週期              |

關鍵敘述：「Capcom uses Amazon DynamoDB to meet this demand with single-digit millisecond response times」。

## 判讀

Capcom 案例揭露三個遊戲後端 KV 的工程重點。

1. **遊戲後端 KV = 跨遊戲共用基礎設施**：Resident Evil / Street Fighter / Monster Hunter 是不同類型遊戲（單機+多人 / 對戰 / 合作打怪）、卻共用 *同一套後端 KV*。這個共用降低了單一遊戲的維運成本、也讓新遊戲上線時不用重做基礎設施。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 multi-tenant platform。
2. **single-digit ms response time = 玩家體感「即時」的底線**：戰鬥動作、技能釋放、玩家對戰都要次秒級反應、超過 10ms 就「卡」。這個延遲門檻反推 Capcom 必須用 sub-region cache（ElastiCache / 本地 game server）+ DynamoDB DAX、不能單靠 DynamoDB。對應 [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 的延遲反推。
3. **「工程資源從 DB 運維轉到遊戲品質」是 managed 服務的真實價值**：Capcom 不是 IT 公司、是遊戲公司。把 DBA 時間從「Postgres patching、replication 設定、backup 排程」釋放到「遊戲機制設計、玩家行為分析」、才是 30% 成本下降的本質。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的人力成本工程化。

需要警惕：「billions of requests」沒指明時間單位（每秒、每天、每月）。讀案例時要找具體單位、不要直接套用到自家。

## 策略

可重用的工程做法：

1. **遊戲後端 KV 用 DynamoDB / Cosmos DB / Bigtable**：partition key 用 player_id 天然均勻、不會 hot partition。對應 [01 資料庫模組](/backend/01-database/) 的 schema 設計。
2. **EKS 跑 game server、不直接連 DynamoDB**：game server 處理遊戲邏輯（戰鬥、配對、防作弊）、DynamoDB 處理持久狀態。中間用 DAX 或 ElastiCache 減少 DynamoDB 呼叫。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/)。
3. **多 IP / 多遊戲共用平台是降本核心**：每個新遊戲不重做基礎設施、共用同一套 DynamoDB + EKS。跟 [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的「single-tenant per game」對照 — 不同 IP 公司有不同取捨。

跨平台等效：GCP Bigtable + GKE + Memorystore、Azure Cosmos DB + AKS + Cache for Redis 都可實作對等架構。

## 下一步路由

- 對照其他遊戲後端 → [9.C12 Riot Games EKS](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)（cluster 隔離 vs 共用）
- 想設計遊戲 KV → [01 資料庫模組](/backend/01-database/) + [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)
- 想理解 sub-ms latency 反推 → [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) + [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/)
- 想規劃遊戲 KV access pattern 與 single-table design → [DynamoDB single-table design](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)
- 想評估遊戲流量的 on-demand vs provisioned → [DynamoDB on-demand vs provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)

## 引用源

- [CAPCOM Case Study](https://aws.amazon.com/solutions/case-studies/capcom/)
- [Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
- [Powering Gaming Applications with Amazon DynamoDB](https://aws.amazon.com/blogs/big-data/powering-gaming-applications-with-amazon-dynamodb/)
