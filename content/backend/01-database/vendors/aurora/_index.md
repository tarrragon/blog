---
title: "AWS Aurora"
date: 2026-05-13
description: "AWS managed PostgreSQL / MySQL、storage / compute 分離、+75% 效能改善的 production 證據"
weight: 7
tags: ["backend", "database", "vendor", "aurora", "sql"]
---

Aurora 是 AWS managed PostgreSQL / MySQL、把 storage layer 重寫成跨 AZ 分散式 log service、保留 wire protocol 相容。Netflix 把多套 RDBMS 統一到 Aurora（+75% 效能、-28% 成本）、DraftKings 撐每分鐘 100 萬 ops 體育博彩、Standard Chartered 跨 7 個受監管市場、FanDuel 處理 Super Bowl 5-10 倍峰值 — 是 SQL OLTP managed 服務的代表。

## 定位：storage / compute 分離的 SQL

Aurora 跟傳統 PostgreSQL / MySQL primary 最大差異是 *storage layer 重寫*。傳統 SQL primary 把 storage 跟 CPU / RAM 綁定、storage 擴容要換 instance、replication lag 受 compute 影響。Aurora 把 storage 拉到分散式 log service、跨 6 個 storage node（3 AZ × 2 node）、storage 跟 compute 獨立擴。

**容量特性**：

- 單一 cluster 最高 storage：128 TB
- 最多 15 個 read replica（單 region 內）
- read replica replication lag：10-30ms（vs 傳統 PostgreSQL 跨 AZ 可能秒級）
- 跨 AZ failover：< 30 秒（promote read replica）
- Aurora Global Database 跨 region replication：< 1 秒典型 lag

**為什麼這個分離很重要**：

- 傳統 PostgreSQL primary 上的 read replica 都靠 logical replication、會跟著 primary write load 走慢
- Aurora storage 直接複製到 6 個 storage node、read replica 從 storage 讀、不靠 primary
- → read replica 大幅減少 lag、可以撐更多 OLTP read traffic
- 對應 [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) +75% 效能改善的關鍵原因

## 適用場景

按公開 case 提煉的典型適用場景：

**1. 既有 PostgreSQL / MySQL 應用想要 managed**：

- wire protocol 相容、應用層幾乎不必改
- ORM / driver / SQL 不必動
- 對應案例：[9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 多套 RDBMS（PostgreSQL、MySQL、Oracle）統一到 Aurora、+75% 效能、-28% 成本

**2. 金融交易 / 體育博彩 OLTP**：

- 強 ACID transaction
- 多 read replica 處理 query traffic、不影響寫
- 對應案例：[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 每分鐘 100 萬 ops、200 個獨立資料庫、Super Bowl 流量 +50% 無影響

**3. 受監管產業跨市場部署**：

- 每個市場一個獨立 cluster、合規分割
- 對應案例：[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 7 個受監管市場、各自獨立 Aurora、總吞吐 4000 TPS、10x 提升

**4. 高峰流量 + 多 read replica 擴容**：

- read 高峰用 read replica 接、write 走 primary
- 對應案例：[9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 5-10x Super Bowl 峰值、直播 + 投注雙工作負載

**5. Aurora Serverless v2 適用場景**：

- 流量 unpredictable + sustained workload
- 自動 scale CPU / RAM、不必管 instance
- 適合：dev / test 環境、流量稀疏的多 tenant SaaS

**6. Aurora Global Database**：

- 跨 region async replication（< 1 秒 typical）
- DR + 跨地理 read（write 在 primary region、read 可從 secondary region）
- 不是 multi-region active-active（要那個用 Aurora DSQL）

## 不適用場景

**1. 跨雲需求**：

- Aurora 是 AWS-only、wire protocol 相容但 storage 是 AWS 專屬
- 替代：自管 PostgreSQL / MySQL on Kubernetes

**2. 需要最新 upstream PostgreSQL / MySQL 特性**：

- Aurora 通常落後 upstream 1-2 個 major version
- 替代：RDS PostgreSQL（更接近 upstream）

**3. 極端寫入吞吐**：

- 單一 primary 寫入受 storage 設計限制（雖然比 PostgreSQL 快）
- > 100K WPS 級別、考慮 sharding、CockroachDB、或 DynamoDB
- 對應 [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — RDB connection limit 是 bottleneck、改 DynamoDB

**4. 全球 multi-region active-active write**：

- Aurora Global Database 是 async、有 lag、不能多 region 同時寫
- 替代：Aurora DSQL（2024 推出）、Spanner、Cosmos DB

**5. 預算敏感的小 workload**：

- Aurora 比 self-managed PostgreSQL 貴 20-30%
- 小流量場景、自管 PostgreSQL on EC2 或 RDS 更便宜

## 跟其他 vendor 的取捨

**vs RDS PostgreSQL / MySQL（同 AWS）**：

- Aurora：storage / compute 分離、更多 read replica、更快 failover、跨 AZ 自動 replication
- RDS：純 managed PostgreSQL / MySQL、不重寫 storage、更接近 upstream
- 選 Aurora：需要 scale read replica 或 cross-AZ failover < 30 秒
- 選 RDS：需要最新 upstream 特性、預算更敏感

**vs 自管 PostgreSQL / MySQL**：

- Aurora：託管、零 ops、自動 backup / failover
- 自管：彈性高、可自己 tuning、跨雲可用、預算可控
- 選 Aurora：團隊不想養 DBA、AWS 生態深
- 選自管：跨雲需求、需要客製化、預算極敏感

**vs CockroachDB**：

- Aurora：single-region scaling（一個 region 內擴）、AWS-only
- CockroachDB：multi-region 強一致、跨雲可用、PostgreSQL wire protocol
- 選 Aurora：AWS-only + single-region OLTP
- 選 CockroachDB：需要 multi-region 強一致 + 不想 vendor lock-in

**vs Aurora DSQL（AWS 2024 推出）**：

- Aurora：single-region scaling、傳統 OLTP
- Aurora DSQL：multi-region active-active write、serverless、強一致
- 選 Aurora：流量集中在一個 region
- 選 Aurora DSQL：需要全球 active-active

**vs DynamoDB**：

- 詳見 [DynamoDB vendor page](/backend/01-database/vendors/dynamodb/) 對比段。Aurora 是 SQL、DynamoDB 是 KV、適用場景不同。

**vs Azure SQL Hyperscale**：

- 設計理念類似（storage / compute 分離）
- Aurora 在 AWS、Hyperscale 在 Azure
- 對應案例：[9.C32 Clearent](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) — Azure 生態的同類設計、5 億 payment txn / 年

## 容量規劃要點

從 09 案例庫提煉的 Aurora 容量規劃實踐：

**1. read replica 是擴 read traffic 的主要工具**：

- 最多 15 個 read replica、replication lag 10-30ms
- read replica autoscaler 按 CPU / connection 自動加減
- 對應 [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 用多個 read replica 處理「比賽期間用戶查 balance」流量

**2. 200 個獨立 cluster 模式**：

- Aurora 不要試圖一個大 cluster 撐全部
- 按業務切多個小 cluster（[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 200 個）、降低 [blast radius](/backend/knowledge-cards/blast-radius/)
- 對應 microservice 私有 store（[9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 同樣思維）

**3. Aurora I/O-Optimized**：

- 2023-05 推出的 storage 配置
- 適合 I/O-heavy workload（write 多、scan 多）
- 比 standard storage 貴、但少 I/O 收費
- 對應 [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 用 I/O-Optimized 加速

**4. Aurora Serverless v2**：

- ACU（Aurora Capacity Unit）為單位、自動 scale 0.5-128 ACU
- 適合 dev / test、稀疏 workload、unpredictable burst
- 不適合：sustained predictable high workload（provisioned 便宜）

**5. Cross-region Global Database**：

- < 1 秒 typical replication lag、但是 async
- secondary region 可 read、不能 write
- DR 切換通常 1-2 分鐘
- 對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 跨市場各自獨立 Aurora（不用 Global Database、合規不允許）

**6. Connection pool 仍是隱性限制**：

- Aurora 跟傳統 PostgreSQL 一樣有 connection pool 上限
- 應用層 + Aurora 之間建議用 RDS Proxy 做 pool 共享
- 對應 [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — RDB connection limit 是 surge 場景的 bottleneck（雖然 Lemino 案例是 RDS、不是 Aurora、但機制相同）

## 預計實作話題（後續擴充）

- Aurora storage architecture 深度（[quorum](/backend/knowledge-cards/quorum/)-based、4 of 6 write、3 of 6 read）
- Cross-AZ failover 流程跟 RTO 量測
- Read replica scaling 策略
- Aurora Global Database 跨 region 配置
- Aurora Serverless v2 適用判斷
- Aurora I/O-Optimized vs Standard 成本對比
- 從自管 PostgreSQL / MySQL 遷到 Aurora
- 多 cluster 按業務切分模式
- RDS Proxy 跟 connection pool 整合
- 跟 Aurora DSQL 的取捨

## 案例對照

| 案例                                                                                                  | 規模                                          | 教學重點                           |
| ----------------------------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------- |
| [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)         | 1M ops/min、<1ms reads、6ms writes、200 個 DB | 體育博彩金融帳本、按業務切 cluster |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 4000 TPS、7 個受監管市場、10x 提升            | 受監管金融跨市場部署               |
| [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)                 | +75% 效能、-28% 成本                          | 多套 RDBMS 統一到 Aurora           |
| [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)          | Super Bowl 5-10x peak                         | 直播 + 投注雙工作負載              |

## 常見陷阱

- **誤以為 Aurora 等於無限擴**：寫吞吐還是受 primary 限制、不是線性擴
- **不用 read replica**：把所有 query 打 primary、白白浪費 read replica scaling 能力
- **跨 region 強一致誤解**：Global Database 是 *async* 複製、不是 multi-region active-active
- **connection pool 忽略**：Aurora 仍是 PostgreSQL / MySQL、connection 上限有效
- **單一巨大 cluster**：把所有業務塞進一個 cluster、blast radius 大、應該按業務切

## 下一步路由

- 平行：[DynamoDB vendor page](/backend/01-database/vendors/dynamodb/)（NoSQL 對比）
- 上游：[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) / [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（從 RDS / 自管遷到 Aurora）
- 跨模組：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)
- 官方：[Amazon Aurora](https://aws.amazon.com/rds/aurora/)、[Aurora storage architecture](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.StorageReliability.html)
