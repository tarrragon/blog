---
title: "CockroachDB"
date: 2026-05-13
description: "分散式 SQL、PostgreSQL 相容、跨區強一致、Spanner 的開源 / 跨雲替代"
weight: 4
tags: ["backend", "database", "vendor", "cockroachdb", "sql", "distributed"]
---

CockroachDB 是分散式 SQL、PostgreSQL wire protocol 相容、跨 region 強一致。設計理念近 Spanner（線性化、跨 region quorum）、但不用 TrueTime hardware（用 HLC + Raft）、是 open source + 跨雲可用的全球 OLTP 選擇。

## 定位：Spanner 的開源 / 跨雲替代

CockroachDB 跟 Spanner 解決同一個問題（跨 region 強一致 SQL）、但定位不同：

- Spanner：GCP-only、managed only、用 TrueTime hardware
- CockroachDB：開源（雙授權）、可自管 + Cockroach Cloud、跨 AWS / GCP / Azure / on-prem、用 HLC + Raft 不靠專屬硬體

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
- 不想 GCP-only（Spanner）或 AWS-only（Aurora DSQL）
- 對應 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的選型決策

**2. PostgreSQL wire protocol 相容路徑**：

- 既有 PostgreSQL 應用想升級到分散式
- 應用層改動小（保留 PostgreSQL driver / ORM）
- 注意：不是 100% PostgreSQL 相容、有些 feature 缺（部分 extension、特定 query 行為）

**3. 自管 on-prem / hybrid**：

- 金融 / 受監管產業需要 on-prem
- Spanner / Aurora DSQL 都 cloud-only
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
- 跨洲 quorum 100ms+ 不可避免

**4. 預算極敏感的小 workload**：

- CockroachDB 至少 3 個節點（Raft quorum）
- 跟 single-instance PostgreSQL 比較貴

**5. 需要 PostgreSQL 進階特性**：

- 部分 PostgreSQL extension 不支援
- partial index、exclusion constraint 等可能缺

## 跟其他 vendor 的取捨

**vs Spanner（GCP）**：

- CockroachDB：開源、跨雲、可自管
- Spanner：GCP-only、TrueTime hardware、Google 規模驗證
- 選 CockroachDB：跨雲 / on-prem 需求
- 選 Spanner：GCP 生態 + 不想 ops + 想要 Google 規模驗證的成熟度

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
- 選 CockroachDB：必須跨 region 強一致
- 選 PostgreSQL：single-region 夠用（90% 場景）

**vs Aurora（single-region scaling）**：

- CockroachDB：multi-region 強一致
- Aurora：single-region scaling、跨 region 是 async Global Database
- 選 CockroachDB：需要 multi-region write
- 選 Aurora：single-region scaling + AWS 生態

## 容量規劃要點

**1. Node count + zone / region 配置**：

- 至少 3 個節點（Raft quorum）
- multi-region 通常 9+ 節點（3 region × 3 replica）
- Survival Goals 配置決定每 region 復原能力

**2. Range（CockroachDB 的 partition）**：

- 跟 DynamoDB partition、Spanner split 同類
- CockroachDB 自動 split 大 range
- 應用層不必管 sharding

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

## 預計實作話題（後續擴充）

- HLC + Raft consensus 工作原理
- Survival Goals 配置（zone-level / region-level）
- Locality-aware schema design
- 從 PostgreSQL 遷到 CockroachDB
- Multi-region table 配置（regional / global tables）
- CockroachDB Cloud serverless 適用判斷
- 跟 Aurora DSQL / Spanner 的決策樹

## 案例對照

CockroachDB 沒有直接的 09 case（多數 09 case 在 vendor managed 上）、但作為「全球分散式 SQL 開源替代」在多處被討論：

| 案例（對比參考）                                                                                      | 跟 CockroachDB 的關係                           |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)         | 設計理念對標、CockroachDB 是開源版本            |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 受監管金融、CockroachDB 可作為 on-prem 替代候選 |

## 常見陷阱

- **single-region 用 CockroachDB**：浪費分散式開銷、PostgreSQL 便宜很多
- **跨洲 active-active 期待低延遲**：物理限制、跨洲 quorum 100ms+
- **PostgreSQL extension 假設**：部分 extension 不支援、應用要驗證
- **不規劃 Survival Goals**：default 配置可能不符合 RTO / RPO 需求
- **backup chain 過長**：incremental 不 full、recovery time 變長

## 下一步路由

- 平行：[Spanner vendor](/backend/01-database/vendors/spanner/)、[Aurora vendor](/backend/01-database/vendors/aurora/)、[PostgreSQL vendor](/backend/01-database/vendors/postgresql/)
- 上游：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) — 完整選型對比
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)
- 官方：[CockroachDB Documentation](https://www.cockroachlabs.com/docs/)
