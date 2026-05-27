---
title: "9.C24 Genesys：用 DynamoDB 在 15 region 跑出 99.999% 可用性"
date: 2026-05-12
description: "Genesys 客服平台用 DynamoDB 為預設資料層、跨 15 主 region + 5 衛星 region、達成 12 個月 99.999% 可用性"
weight: 24
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "low-latency-sustained"]
---

這個案例的核心責任是說明 B2B SaaS 平台的容量規劃跟 C2C 案例的本質差異。Genesys 服務的是 *客戶服務中心* — 客戶停線 = 全終端使用者打不通電話、客戶會失去信任。99.999% 可用性（年停機 5 分鐘）對 B2B 客服 SaaS 是合約義務、不是行銷敘述。

## 觀察

Genesys Cloud 在 DynamoDB 的關鍵數字（引自 [Genesys DynamoDB Case Study](https://aws.amazon.com/solutions/case-studies/genesys-dynamodb-case-study/)）：

| 指標        | 數字                                  |
| ----------- | ------------------------------------- |
| 客戶組織    | 8,000+ 個                             |
| 服務國家    | 100+ 個                               |
| 主 region   | 15 個                                 |
| 衛星 region | 5 個                                  |
| 可用性      | 99.999%（截至 2024-07-31 的 12 個月） |
| 微服務數    | 數百個                                |
| 資料層      | DynamoDB 為預設、用其他要 justify     |

關鍵架構決策（引述 Chief Architect Rob Gevers）：「Amazon DynamoDB is our primary data layer by default, and teams have to justify the use of something else.」

## 判讀

Genesys 案例揭露三個 B2B SaaS 平台容量規劃重點。

1. **B2B 可用性目標跟 C2C 不同**：B2C 大型網站可能接受 99.9%（年停機 8.76 小時）、B2B SaaS 經常合約規定 99.95% 或 99.99%、客服平台類甚至要 99.999%（年停機 5 分鐘）。每多一個 9、容量規劃跟運維成本指數成長。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 SLO 等級設計。
2. **「DynamoDB 為預設、用其他要 justify」是規模化平台的工程治理**：跟 [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 整合到 Aurora 是同樣訴求、不同實作 — Genesys 選 DynamoDB 為基準是因為「Multi-region active-active」+「自動 scaling」+「99.999% SLA」的組合最容易達成 5 個 9 目標。對應 [01 資料庫模組](/backend/01-database/) 的 DB 預設選型。
3. **15 主 region + 5 衛星 region = 全球客戶就近接入**：客戶服務有強烈延遲敏感（agent 操作介面卡 1 秒、客服效率掉一半）、必須在客戶所在地有 region。跟 [9.C12 Riot Games 246 cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的延遲驅動 region 部署同類思維。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的地理分散規劃。

需要警惕：

- 「99.999% over 12 months」是 *截至特定時間點的歷史值*、不代表「未來持續達成」。可用性是滾動指標、不是恆久承諾。
- 案例 *沒有* 提具體 QPS / RPS、訊息量、延遲分布。讀者要對 *策略* 學習、具體數字需要自己壓測。

## 策略

可重用的工程做法：

1. **B2B SaaS 平台優先選 multi-region active-active 資料層**：DynamoDB Global Tables、Cosmos DB Multi-Region Write、Spanner multi-region 都是候選。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的全球一致性取捨。
2. **「預設 DB」原則簡化 onboarding**：新團隊不用評估十種 DB、預設用 X、特殊需求再 justify。減少團隊認知負擔、加速產品開發。對應 [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 DB 整合。
3. **99.999% 必須有 redundancy 在每一層**：DNS、load balancer、application、database、storage 都要跨 region active-active。任何一層 single-region 就破壞整體 SLO。對應 [05 部署平台模組](/backend/05-deployment-platform/) 跟 [06 可靠性驗證模組](/backend/06-reliability/)。
4. **多 region 是成本 vs 可用性的硬取捨**：15 個 region 的成本約是 1 個 region 的 15 倍 — 對 B2B SaaS 是合理投資、對 B2C 通常不划算。

跨平台等效：Azure Cosmos DB Multi-Region Write、GCP Spanner multi-region、Cassandra multi-DC 都可實作對等架構。差異是 region 數量、SLA 承諾、跨 region 延遲。

## 下一步路由

- 想設計 B2B SaaS 可用性 → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) + [06.6 SLO 與 Error Budget 政策](/backend/06-reliability/slo-error-budget/)
- 想設計多 region 資料層 → [01 資料庫模組](/backend/01-database/) + [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)
- 想做 DB 統一治理 → [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) + [00 服務選型模組](/backend/00-service-selection/)
- 想規劃跨 region 容量 → [9.6 容量規劃模型](/backend/09-performance-capacity/) + [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)
- 想理解 DynamoDB 99.999% 背後的 partition / GSI 設計 → [DynamoDB partition key 反模式](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) + [DynamoDB GSI / LSI 設計](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)
- 想對應 global tables 多 region 寫衝突 → [DynamoDB global tables 寫衝突](/backend/01-database/vendors/dynamodb/global-tables-conflict/)

## 引用源

- [Genesys Achieves 99.999% Availability Using Amazon DynamoDB](https://aws.amazon.com/solutions/case-studies/genesys-dynamodb-case-study/)
- [Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
