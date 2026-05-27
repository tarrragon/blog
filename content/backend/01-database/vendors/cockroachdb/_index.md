---
title: "CockroachDB"
date: 2026-05-13
description: "分散式 SQL、PostgreSQL 相容、跨區強一致、Spanner 的開源 / 跨雲替代"
weight: 4
tags: ["backend", "database", "vendor", "cockroachdb", "sql", "distributed"]
---

CockroachDB 是分散式 SQL、PostgreSQL wire protocol 相容、跨 region 強一致。設計理念接近 Spanner（線性化、跨 region [quorum](/backend/knowledge-cards/quorum/)），但採 HLC + Raft 而非 TrueTime hardware，是 open source + 跨雲可用的全球 OLTP 選擇。

## 教學路線：Distributed SQL 與跨雲一致性

CockroachDB 服務頁的教學目標是把 PostgreSQL-like 介面背後的 range sharding、Raft replication、serializable transaction、leaseholder 與 region placement 說清楚。讀者讀完後要能判斷 distributed SQL 何時能取代自管 sharding，何時會把 latency 與 retry 壓力推回應用層。

| 學習段               | 核心問題                                                           | 對應段落                                                                   |
| -------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Distributed SQL      | SQL 介面如何藏住 range sharding 與 Raft replication                | 定位、容量特性                                                             |
| Serializable default | transaction retry、contention、latency 如何影響應用設計            | 容量規劃要點、[Isolation Level](/backend/knowledge-cards/isolation-level/) |
| Region placement     | multi-region table、leaseholder、survival goal 如何服務產品需求    | 適用場景、跟其他 vendor 的取捨                                             |
| Migration pressure   | 從 PostgreSQL / MySQL 或自管 sharding 過來時要檢查哪些差異         | 預計實作話題、案例對照                                                     |
| 替代路由             | 何時留 PostgreSQL、用 Spanner、Aurora DSQL 或 application sharding | 不適用場景、下一步路由                                                     |

## 定位：Spanner 的開源 / 跨雲替代

CockroachDB 跟 Spanner 解決同一個問題（跨 region 強一致 SQL）、但定位不同：

- Spanner：GCP managed service、用 TrueTime hardware
- CockroachDB：開源（雙授權）、可自管 + Cockroach Cloud、跨 AWS / GCP / Azure / on-prem、用 HLC + Raft

選 CockroachDB 的核心訴求：需要跨 region 強一致 SQL + 想避免雲商 lock-in、想自管或跨雲部署。

詳見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的 CockroachDB 段。

## 容量特性

**節點即容量單位**：

- 跟 Spanner 同樣設計、節點數量決定容量
- 每節點承擔 query + storage + replication
- 線性擴展（理論）、實際依 query pattern

**跨 region 配置**：

- multi-region survival goal（zone-level / region-level）
- 跨 region quorum 必要、決定 latency
- 跟 Spanner 同樣的物理限制（跨洲 100ms+）

**Replication**：

- Raft consensus per range
- 預設 3-replica
- 可配置每個 region 不同 replica count（Survival Goals）

## 適用場景

**1. 需要跨 region 強一致 SQL + 跨雲**：

- multi-region active-active write
- GCP-only（Spanner）或 AWS-only（Aurora DSQL）和部署策略不合
- 對應 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的選型決策

**2. PostgreSQL wire protocol 相容路徑**：

- 既有 PostgreSQL 應用想升級到分散式
- 應用層改動小（保留 PostgreSQL driver / ORM）
- 注意：PostgreSQL 相容要以實際 query、extension 與 migration test 驗證

**3. 自管 on-prem / hybrid**：

- 金融 / 受監管產業需要 on-prem
- Spanner / Aurora DSQL 以 cloud service 為主
- CockroachDB 可自管

**4. 想避免單一 vendor 全球分散式 lock-in**：

- 開源 + 跨雲、可遷移性高
- 但企業版功能要付費（CockroachDB Cloud 或 Enterprise license）

## 不適用場景

**1. single-region OLTP 夠用**：

- 90% 場景 PostgreSQL / Aurora 已夠
- CockroachDB 有分散式 overhead（每個寫經 Raft）
- 替代：PostgreSQL、Aurora、MySQL

**2. 極端高吞吐 single-query**：

- CockroachDB 寫入有 Raft 開銷、單機吞吐 < PostgreSQL
- 整體吞吐靠 scale-out 達成、單一 query latency 較高

**3. 跨洲低延遲（< 50ms）**：

- 跟 Spanner 同樣物理限制
- 跨洲 quorum 100ms+ 是物理成本

**4. 預算極敏感的小 workload**：

- CockroachDB 至少 3 個節點（Raft quorum）
- 跟 single-instance PostgreSQL 比較貴

**5. 需要 PostgreSQL 進階特性**：

- 部分 PostgreSQL extension 或行為需要替代方案
- partial index、exclusion constraint 等可能缺

## 跟其他 vendor 的取捨

**vs Spanner（GCP）**：

- CockroachDB：開源、跨雲、可自管
- Spanner：GCP-only、TrueTime hardware、Google 規模驗證
- 選 CockroachDB：跨雲 / on-prem 需求
- 選 Spanner：GCP 生態 + managed operation + Google 規模驗證的成熟度

**vs Aurora DSQL（AWS 2024）**：

- CockroachDB：跨雲、生產驗證較久
- Aurora DSQL：AWS-only、serverless、新（2024）
- 選 CockroachDB：跨雲、想避免 AWS lock-in
- 選 Aurora DSQL：AWS 生態 + 已用 PostgreSQL + serverless 訴求

**vs TiDB**：

- CockroachDB：PostgreSQL wire、英語 / 歐美生態深
- TiDB：MySQL wire、亞洲生態深、HTAP（OLTP + OLAP 同庫）
- 選 CockroachDB：PostgreSQL 應用、跨雲
- 選 TiDB：MySQL 應用、需要 OLAP 整合、亞洲市場

**vs PostgreSQL（傳統）**：

- CockroachDB：分散式、跨 region 強一致
- PostgreSQL：single-primary、跨 region 是 async replication
- 選 CockroachDB：需要跨 region 強一致
- 選 PostgreSQL：single-region 夠用（90% 場景）

**vs Aurora（single-region scaling）**：

- CockroachDB：multi-region 強一致
- Aurora：single-region scaling、跨 region 是 async Global Database
- 選 CockroachDB：需要 multi-region write
- 選 Aurora：single-region scaling + AWS 生態

**vs MySQL + Vitess（self-managed distributed MySQL）**：

- CockroachDB：PostgreSQL wire、transparent sharding（range-based）、跨 region 強一致內建
- MySQL + Vitess：MySQL wire、application 層配 keyspace + shard key、跨 region 靠 application + async replication
- 選 CockroachDB：PostgreSQL 應用 + transparent multi-region + 想避開 Vitess operation burden
- 選 MySQL + Vitess：MySQL 應用 + 有 DBA 養 Vitess + 已是 YouTube / Slack 規模

## 容量規劃要點

**1. Node count + zone / region 配置**：

- 至少 3 個節點（Raft quorum）
- multi-region 通常 9+ 節點（3 region × 3 replica）
- Survival Goals 配置決定每 region 復原能力

**2. Range（CockroachDB 的 partition）**：

- 跟 DynamoDB partition、Spanner split 同類
- CockroachDB 自動 split 大 range
- application 主要管理 query locality、transaction retry 與 region placement

**3. Locality 配置**：

- 跟 Spanner 一樣可以指定 voting region
- 寫入 locality 影響跨 region latency

**4. Backup / restore**：

- CockroachDB 原生 backup 支援 cluster-level snapshot
- 增量 backup 支援
- 注意：incremental backup chain 可能很長、定期 full backup

**5. Self-managed vs Cockroach Cloud**：

- Self-managed：需要 ops team、可跨雲 / on-prem
- Cockroach Cloud：managed、跨 cloud（AWS / GCP / Azure）、可考慮 serverless tier

## Deep article（已完成）

本批 5 篇 deep article 已完成、覆蓋 CockroachDB 從 consensus 機制到 distributed SQL 選型決策的核心 production 議題：

| 主題                                                                | 文章                                                                    | 對應 production 議題                                                                         |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| HLC + per-range Raft、leaseholder、寫入 latency 結構                | [hlc-raft-consensus](hlc-raft-consensus/)                               | DoorDash Aurora 撞牆訊號（1.636 M QPS）、Netflix 380+ artery of small DBs 容量規劃顆粒       |
| SURVIVE ZONE / REGION FAILURE 倒推、業務 SLO 決定副本拓樸           | [survival-goals](survival-goals/)                                       | Hard Rock RPO=0 倒推、Netflix Gaming 48-node 跨 4 region「為求 survival 而非 latency」反直覺 |
| Serializable default、application 必須包 retry loop、SAVEPOINT 語法 | [transaction-retry-pattern](transaction-retry-pattern/)                 | PG → CockroachDB application contract 重塑、5 種 retry failure mode（跨 case 合成 frame）    |
| REGIONAL BY ROW / TABLE / GLOBAL、跨州合規 + 邏輯一個 cluster       | [locality-aware-schema](locality-aware-schema/)                         | Hard Rock 跨 8 州 sportsbook + AWS Outposts、Outposts 是合規工具不是 latency 工具反直覺判讀  |
| Distributed SQL 三選一決策樹：撞牆訊號分型 + 七問題                 | [aurora-dsql-spanner-decision-tree](aurora-dsql-spanner-decision-tree/) | DB4 cross-vendor entry：DoorDash / Netflix / Hard Rock driver path 識別 + sizing barrier     |

DB4 cross-vendor entry：先看 [aurora-dsql-spanner-decision-tree](aurora-dsql-spanner-decision-tree/) 識別 driver path、再進個別 vendor 深度。

## 後續擴充（仍待補）

- Multi-region table 配置（regional / global tables）
- CockroachDB Cloud serverless 適用判斷
- 從 PostgreSQL 遷到 CockroachDB（playbook）

## Anti-recommendation 與升級路由

CockroachDB 的 PostgreSQL-like 介面會降低導入門檻，但 distributed SQL 的成本會出現在 transaction retry、range lease、multi-region latency 與操作拓樸。這一段先說何時維持 PostgreSQL / Aurora，再說何時升級 CockroachDB、Cockroach Cloud、Spanner、Aurora DSQL 或 Vitess。

| 機制 / 路線               | 維持簡單設計的條件                                           | 升級訊號                                                             | 主要引用路徑                                                                                                                                   |
| ------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| PostgreSQL / Aurora       | single-region primary、async DR、read replica 已滿足需求     | multi-region write、region failure survival、跨雲部署是硬需求        | [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)、[Aurora vendor](/backend/01-database/vendors/aurora/)                           |
| CockroachDB single-region | 需要水平擴容或 future multi-region，但目前在單區運作         | Raft overhead 讓成本高於 PostgreSQL，且沒有 region requirement       | [Distributed SQL](/backend/knowledge-cards/distributed-sql/)                                                                                   |
| CockroachDB multi-region  | 跨雲 / on-prem、PostgreSQL wire、strong consistency 是主需求 | 跨洲 p99 目標過低、transaction retry 影響 user flow                  | [Quorum](/backend/knowledge-cards/quorum/)、[Latency Budget](/backend/knowledge-cards/latency-budget/)                                         |
| Cockroach Cloud           | 團隊仍能自管 Raft、backup、upgrade、node failure             | 想把 operation transfer 給 vendor                                    | [RTO](/backend/knowledge-cards/rto/)、[RPO](/backend/knowledge-cards/rpo/)                                                                     |
| Spanner                   | 跨雲或自管是硬需求                                           | GCP managed、TrueTime 成熟度、Google scale evidence 是主訴求         | [Spanner vendor](/backend/01-database/vendors/spanner/)                                                                                        |
| Aurora DSQL               | 跨雲 / on-prem 是硬需求                                      | AWS-only、serverless、PostgreSQL 相容與 AWS operation model 是主訴求 | [PG → Aurora DSQL Migration](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)                                                  |
| MySQL + Vitess            | PostgreSQL-like SQL 與 strong consistency 是主需求           | MySQL ecosystem、application sharding 與 Vitess ops 已成熟           | [MySQL Vitess Sharding](/backend/01-database/vendors/mysql/vitess-sharding/)、[Database Sharding](/backend/knowledge-cards/database-sharding/) |

CockroachDB 的簡單路徑是先證明 distributed SQL 的價值大於 retry 與 latency 成本。若 workload 仍是 single-region OLTP，PostgreSQL / Aurora 通常提供更低成本；若跨 region 寫入與一致性是產品承諾，CockroachDB 才成為主要候選。

Transaction retry 的升級路徑要進入 application contract。Serializable default 能保護一致性，但 retry 會把 idempotency、timeout、user-visible latency 與 workflow compensation 帶回應用層；這些條件要在 migration playbook 前先盤點。

## 已知 limitation 與後續路由

CockroachDB overview 目前完成 distributed SQL 判斷。下一輪 deep article / playbook 應補 HLC + Raft、range / leaseholder、multi-region table locality、transaction retry pattern、PostgreSQL compatibility audit、Cockroach Cloud operation 與 PostgreSQL → CockroachDB migration。

## 案例對照

CockroachDB 在 09 案例庫已有三條直接 case 軸線（OLTP 寫入擴展、polyglot 補位、合規邊界），另外兩條對比參考軸線（Spanner 設計理念、受監管金融）一併保留。

### Direct case（CockroachDB 為主角）

| 案例                                                                                                            | 主要工程議題                                                         |
| --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)                  | Aurora Postgres single-primary 1.6 M QPS 撞牆 → multi-primary 解寫入 |
| [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)                 | 380+ cluster 艦隊、Cassandra 不夠用的 transactional workload 補位    |
| [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/) | AWS Outposts + 跨州單一邏輯 DB、Wire Act 合規 + 賽季型擴縮容         |

### 對比參考案例

| 案例（對比參考）                                                                                      | 跟 CockroachDB 的關係                           |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)         | 設計理念對標、CockroachDB 是開源版本            |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 受監管金融、CockroachDB 可作為 on-prem 替代候選 |

CockroachDB direct case 的讀法是「寫入擴展（DoorDash）→ polyglot 補位（Netflix）→ 合規邊界（Hard Rock Digital）」三條軸線；對比案例則提醒讀者：Spanner 提供 global consistency 的成熟對照，受監管金融類案例提醒部署位置、合規邊界與自管能力常和一致性需求同時決定 vendor。

## 反向 sibling 路由

CockroachDB 的反向 sibling 路由用來把 PostgreSQL 相容性和 distributed SQL 責任拆開。若讀者從 PostgreSQL 章節過來，先讀 [PostgreSQL → CockroachDB migration](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)；若只是要 managed SQL 與 storage autoscale，先回 [Aurora vendor](/backend/01-database/vendors/aurora/)；若要 Google Cloud 原生 external consistency 與 fully managed control plane，再對照 [Spanner vendor](/backend/01-database/vendors/spanner/)。

這條路由的判準是「應用是否能承擔 distributed transaction 的語意差異」。SQL dialect 相近只降低 migration entry cost，真正的交付風險在 transaction retry、hot range、survival goal、backup restore 與 locality design。

## 常見陷阱

- **single-region 用 CockroachDB**：浪費分散式開銷、PostgreSQL 便宜很多
- **跨洲 active-active 期待低延遲**：物理限制、跨洲 quorum 100ms+
- **PostgreSQL extension 假設**：部分 extension 或 SQL 行為需要替代方案，應用要驗證
- **不規劃 Survival Goals**：default 配置可能不符合 RTO / RPO 需求
- **backup chain 過長**：incremental 不 full、recovery time 變長

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[Spanner vendor](/backend/01-database/vendors/spanner/)、[Aurora vendor](/backend/01-database/vendors/aurora/)、[PostgreSQL vendor](/backend/01-database/vendors/postgresql/)
- 上游：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) — 完整選型對比
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)
- Last reviewed：2026-05-22（PostgreSQL compatibility / survival goal / managed offering 屬時間敏感 claim）
- 官方：[CockroachDB Documentation](https://www.cockroachlabs.com/docs/)
