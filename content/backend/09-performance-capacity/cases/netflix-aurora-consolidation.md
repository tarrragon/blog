---
title: "9.C23 Netflix：把關聯式 DB 統一到 Aurora、效能 +75%、成本 -28%"
date: 2026-05-12
description: "Netflix 把多套關聯式 DB 統一到 Aurora、效能提升 75%、成本下降 28%、串流數十億小時"
weight: 23
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "aws", "sustained-growth"]
---

這個案例的核心責任是說明 Netflix 在 AWS 上的「資料庫統一」決策、跟 [9.C12 Riot Games EKS 多集群](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 形成對照。Riot 走「single-tenant per workload、246 個 cluster」、Netflix 走「跨 application 統一 Aurora、減少 DB 種類」 — 兩條路徑都是大規模平台的 *合理* 選擇、但工程哲學完全不同。

## 觀察

Netflix 在 Aurora 整合的關鍵敘述（引自 [Netflix consolidates relational database infrastructure on Amazon Aurora](https://aws.amazon.com/blogs/database/netflix-consolidates-relational-database-infrastructure-on-amazon-aurora-achieving-up-to-75-improved-performance/)）：

| 指標       | 數字                        |
| ---------- | --------------------------- |
| 效能提升   | up to 75%                   |
| 成本下降   | 28%                         |
| 月串流時數 | billions of hours           |
| 服務地理   | global                      |
| 整合範圍   | 多套 relational DB → Aurora |
| 微服務架構 | 全球分散式 microservices    |
| 容器編排   | Amazon EKS                  |

Netflix 整體 AWS 使用：「Netflix uses AWS to deliver billions of hours of content monthly and runs its analytics platform for optimum performance of its global service. AWS enables Netflix to quickly deploy thousands of servers and terabytes of storage within minutes.」

## 判讀

Netflix Aurora 整合揭露三個大規模平台 DB 治理重點。

1. **「DB 種類太多」本身是規模化的成本**：Netflix 過往用 PostgreSQL、MySQL、Oracle 等不同 RDB、每個都需要不同 DBA 知識、不同備份、不同 monitoring 流程。整合到 Aurora 不只是「換 DB」、是「降低運維 surface area」、釋放工程資源。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的人力成本工程化、跟 [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 同類訴求。
2. **75% performance improvement 是 Aurora storage layer 的本質優勢**：Aurora 把 storage 跟 compute 分離、storage 用分散式 log-based 設計、replication 在 storage 層處理、不在 compute 層 — 這讓 read replica 不會受 master 寫入壓力影響、性能曲線比傳統 RDB 平滑。對應 [01 資料庫模組](/backend/01-database/) 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的儲存層 vs 計算層分離。
3. **Netflix 的 DB 工作負載大多是「微服務私有 store」**：Netflix 微服務各自有自己的 Aurora cluster、不共用 — 跟 monolith 「一個大 DB 撐全部」相反。這層架構讓「DB 容量規劃」變成「每個微服務的容量規劃」、複雜度分散。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 service decomposition、跟 [9.C7 Lyft 微服務](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)。

需要警惕：

- 「effective 75% improvement」是 *跨多個 workload 的最大改善幅度*、不是「每個 workload 都 +75%」。實際每個 workload 改善幅度從 10% 到 75% 不等。
- Netflix 數據層遠不止 Aurora — 還有 Cassandra（playback metadata）、EVCache（cache layer）、Iceberg（data warehouse）。Aurora 主要是「需要 ACID 的 OLTP 工作負載」、不是「all-purpose store」。

## 策略

可重用的工程做法：

1. **DB 種類整合是規模化的必要工程**：每多一種 DB 就多一套運維 surface。在能合理 consolidate 的時候整合、降低 ops 複雜度。對應 [00 服務選型模組](/backend/00-service-selection/) 的 vendor diversity 取捨。
2. **storage / compute 分離是 OLTP 擴容的關鍵**：Aurora、Spanner、TiDB 都採類似設計、是現代 cloud DB 的共同特徵。對應 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 的 storage layer 設計。
3. **微服務私有 store 比共用 DB 容量規劃簡單**：每個服務各自管 DB 容量、跨服務 contention 變成 *network 議題* 而非 *DB lock 議題*。
4. **大規模平台必須區分「OLTP 用 Aurora」「analytics 用 data lake」「KV 用 DynamoDB」「cache 用 EVCache」**：Netflix 用各種 DB、不是一招打天下。對應 [00 服務選型模組](/backend/00-service-selection/) 的 polyglot persistence。

跨平台等效：GCP Spanner（替代 OLTP）+ Bigtable（替代 KV）+ BigQuery（替代 analytics）；Azure Cosmos DB（替代多 model）+ SQL Hyperscale + Synapse — 各雲商提供類似 stack。

## 下一步路由

- 對照其他大規模平台 → [9.C12 Riot Games EKS](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)（不同 consolidation 策略）
- 想理解 Aurora 設計 → [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) + [01 資料庫模組](/backend/01-database/)
- 想做 polyglot persistence 選型 → [00 服務選型模組](/backend/00-service-selection/) + [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)
- 想做 DB consolidation 規劃 → [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)

## 引用源

- [Netflix consolidates relational database infrastructure on Amazon Aurora, achieving up to 75% improved performance](https://aws.amazon.com/blogs/database/netflix-consolidates-relational-database-infrastructure-on-amazon-aurora-achieving-up-to-75-improved-performance/)
- [Netflix on AWS](https://aws.amazon.com/solutions/case-studies/innovators/netflix/)
- [Netflix Case Study](https://aws.amazon.com/solutions/case-studies/netflix-case-study/)
