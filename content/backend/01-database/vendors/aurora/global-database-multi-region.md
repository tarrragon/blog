---
title: "Aurora Global Database：跨 region async replication、< 1 秒 lag 與合規 anti-recommendation"
date: 2026-05-27
description: "Aurora Global Database 跨 region storage-level async replication、< 1 秒 typical lag、planned vs unplanned failover RTO 數量級對比、Standard Chartered 合規禁止跨境複製為什麼讓 Global Database 變反指標"
weight: 60
tags: ["backend", "database", "aurora", "global-database", "multi-region", "dr", "deep-article"]
---

Aurora Global Database 是 *跨 region async replication*、< 1 秒 typical lag、最多 5 個 secondary region — 看起來是 multi-region OLTP 的標準解、但 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 揭露一個受監管產業的 anti-recommendation：合規禁止跨境複製場景下、Global Database *違反合規*、要改用每市場獨立 cluster + 應用層市場切換。本文展開 Global Database 適用條件、跟 cross-AZ failover 的 RTO 數量級差、合規邊界、跟 Aurora DSQL / Spanner / CockroachDB 的決策樹。

本文不是 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 而是 Global Database 的實作層教學。前置閱讀建議 [Aurora storage architecture](../storage-architecture/)（理解 storage-level replication）、[Aurora cross-AZ failover RTO](../cross-az-failover-rto/)（對照單 region failover）。

## 問題情境

典型觸發場景：global SaaS / 跨地理金融服務、需要 region-level DR（us-east-1 整 region 失效時 < 5 分鐘恢復寫入）、或跨地理 read（歐洲用戶查美國 primary 延遲 100ms+ 不可接受）、但又不到「multi-region active-active write」需求。

讀者常見的具體疑問：

- 「Global Database 是 sync 還是 async？lag 多少？」
- 「Secondary region 可以寫嗎？」
- 「Region failover 流程跟 cross-AZ 一樣嗎？」
- 「跟 Aurora DSQL / Spanner / CockroachDB 怎麼選？」
- 「合規場景一定要用 Global Database 嗎？」

進一步問題：Global Database 對一般 SaaS 是合理的 DR + 跨地理 read 工具、但對 *受監管產業* 是反指標。[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 7 個受監管市場、各自獨立 Aurora cluster、不用 Global Database — 不是技術不夠、是合規要求「資料不能跨境複製」。讀者規劃 multi-region 架構時、合規維度要在技術維度之前判斷。

## 核心機制：跨 region async storage replication

Aurora Global Database 的 first-class concept 是 *跨 region storage-level async replication*。跟 logical replication / streaming replication 不同、Global Database 在 storage layer 複製、lag 上限相對穩定。

**Architecture**：

- Primary region：1 個 writer cluster + N read replica
- Secondary region：最多 5 個 secondary region、每 region N 個 reader-only cluster（最多 16 個 reader 含 1 個 headless）
- Storage replication：primary region 寫 storage 後 *async* push 到 secondary region storage、不等 ack

**Write path**：

```text
Application
    ↓ writer endpoint (primary region only)
Primary region compute
    ↓ redo log
Primary region storage (4-of-6 quorum)
    ↓ async replication (typical < 1 秒)
Secondary region storage
```

**Read path**：

- Secondary region 直接從 local storage 讀、不需要跨 region 拉
- Read latency 是 secondary region local latency、不是跨 region

**DR 切換 RTO 跟 cross-AZ 對比**：

| 場景               | RTO       | 機制                                        |
| ------------------ | --------- | ------------------------------------------- |
| Cross-AZ failover  | < 30 秒   | storage 跨 AZ 共享、replica 升 primary 即可 |
| Planned failover   | < 2 分鐘  | managed graceful failover、無資料丟失       |
| Unplanned failover | 5-15 分鐘 | 整 region 失效、手動 promote secondary      |

數量級不同 — cross-AZ 是 *seconds*、cross-region planned 是 *minutes*、unplanned 是 *tens of minutes*。

**對應 knowledge card**：[stale-read](/backend/knowledge-cards/stale-read/)、[rpo](/backend/knowledge-cards/rpo/)、[rto](/backend/knowledge-cards/rto/)。

**跟通用 cross-region replication 差在哪**：Aurora 在 storage layer 複製、lag 上限更穩定；vs PostgreSQL logical replication lag 受寫速度影響大、heavy write 期間可能秒級到分鐘級。

## Step-by-step 配置

**建 global cluster**：

```bash
# Step 1：在 primary region 建 global cluster
aws rds create-global-cluster \
  --global-cluster-identifier myglobal \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:123:cluster:primary-cluster \
  --region us-east-1

# Step 2：在 secondary region 加 reader cluster
aws rds create-db-cluster \
  --db-cluster-identifier secondary-cluster \
  --global-cluster-identifier myglobal \
  --engine aurora-postgresql \
  --source-region us-east-1 \
  --region eu-west-1

# Step 3：在 secondary region 建 db instance
aws rds create-db-instance \
  --db-cluster-identifier secondary-cluster \
  --db-instance-identifier secondary-reader-01 \
  --db-instance-class db.r6g.4xlarge \
  --engine aurora-postgresql \
  --region eu-west-1
```

**Application routing**：

```yaml
# 寫永遠去 primary region writer endpoint
primary:
  url: jdbc:postgresql://primary-cluster.cluster-xxx.us-east-1.rds.amazonaws.com/mydb

# read 可走 secondary region reader endpoint（靠近用戶的 region）
secondary-eu:
  url: jdbc:postgresql://secondary-cluster.cluster-ro-xxx.eu-west-1.rds.amazonaws.com/mydb
```

**DR 切換（planned failover）**：

```bash
aws rds failover-global-cluster \
  --global-cluster-identifier myglobal \
  --target-db-cluster-identifier arn:aws:rds:eu-west-1:123:cluster:secondary-cluster
```

切換後 application 端要 *reconfigure connection string* — DNS 不自動切跨 region（vs cross-AZ failover writer endpoint 自動跟）。

**Application reconfiguration 模式**：

- Connection string 用 service discovery（Consul / Route53 health check）動態解析
- 或在 application config 加入 region-aware logic、failover 後切換 active region
- 不能假設 application 自動 reconnect 到新 primary region

**驗證點**：

- `AuroraGlobalDBReplicationLag` < 1 秒
- Planned failover RTO 量測（手動 trigger + heartbeat timestamp diff）
- Application 跨 region read 路徑 latency 符合預期

**Rollback boundary**：promote secondary 後原 primary 變 secondary、不會自動 fallback；rollback 要再做一次 failover。

## 故障模式 / 邊界 case

### Case 1：期待 multi-region active-active write

徵兆：team 在 secondary region application 直連 secondary cluster 寫資料、收到 `cannot execute INSERT in a read-only transaction` 錯誤。

原因：Global Database secondary 是 *reader-only*、寫只能去 primary region。要 active-active write 必須改用其他服務（Aurora DSQL / Spanner / CockroachDB）。

修：

- Application 設計時明確區分 read region vs write region
- 寫操作永遠路由到 primary region、容忍跨 region write latency
- 真的需要 active-active write 才考慮 Aurora DSQL（2024-12 preview / 2025-05 GA）

### Case 2：DNS 不跨 region 自動切

徵兆：手動 failover trigger 後、application 端 connection string 仍指向舊 primary region、寫操作全失敗。

原因：cross-AZ failover writer endpoint DNS 自動跟、cross-region 不會 — Global Database 切換要 application 端管 region-specific connection string。

修：

- Application 用 service discovery（Route53 / Consul / etcd）解析 active primary region
- 部署 region-aware DNS（Route53 latency-based routing + health check）
- Failover 演練要包含 application reconfiguration step、不只是 DB layer

### Case 3：跨 region read 假設 strong consistency

徵兆：用戶在 primary region 寫資料、隨即在 secondary region read、看到舊資料、客訴 inconsistency。

原因：Global Database 是 async replication、< 1 秒 lag 不是 zero、read-after-write 場景仍會看到 stale data。

修：

- 用戶寫操作後短期內 read 走 primary region（read-after-write window）
- 接受最終一致性、application 端做 versioning / timestamp 比對
- 強一致性需求改 Aurora DSQL / Spanner

### Case 4：Lag spike during bulk operation

徵兆：DDL 或 bulk insert 期間 cross-region lag 從 < 1 秒跳到秒級到分鐘級、secondary region read 大量 stale。

原因：Global Database 「< 1 秒」是 typical、heavy write 期間 lag 拉大。Storage-level replication 比 logical 穩定、但 *不是 zero variance*。

修：

- DDL 跟 bulk insert 在低峰期跑、避開跨 region read traffic
- 監測 `AuroraGlobalDBReplicationLag`、spike 超過閾值 trigger application 端 fallback（read 切回 primary region）
- 重要 DDL 用 [pg_repack](https://github.com/reorg/pg_repack) 避免長時間 lag

### Case 5：合規邊界誤用 Global Database — Standard Chartered anti-pattern

徵兆：team 以為 Global Database 是受監管金融的標準 DR 解、配置完才發現監管機構不接受跨境資料複製、被迫拆掉 Global Database 重建獨立 cluster。

[9.C14 Standard Chartered case](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 「判讀」段第 1 點原文：「7 個受監管市場代表 7 個獨立 cluster（資料不能跨境）、容量規劃變成『7 個獨立規劃 × 各自合規門檻』」。

原因：受監管市場資料 *不能跨境複製*、Global Database 本質上就是跨 region storage replication、配置了就違反合規。Standard Chartered 的選擇是 *每市場獨立 cluster*、跨市場 DR 走應用層市場切換、不靠 Global Database。

修：

- 規劃 multi-region 前先確認合規要求（資料駐留、跨境複製禁令、稽核要求）
- 合規禁止跨境複製場景：每市場獨立 cluster + cross-AZ failover 吸收 RTO（見 [cross-az-failover-rto](../cross-az-failover-rto/)）
- 跨市場 DR 設計成 *市場切換*（用戶從 A 市場切到 B 市場）、不是 *資料切換*
- Fleet 拓樸（多市場 → 多 cluster）詳見 [Aurora read replica scaling](../read-replica-scaling/) fleet 治理 SSoT

**scope warning（必明示）**：Standard Chartered case 未公開是 PostgreSQL 還是 MySQL、未公開具體 cost 數字、屬「相關 case study」匿名對照。引用時不能擴寫具體 engine。

### Case 6：Cost trap — cross-region data transfer

徵兆：開了 Global Database 後月帳變高 50%、發現 cross-region data transfer 是主要費用、不是 instance。

原因：Aurora 跨 region replication 走 AWS 內部網路、但 *cross-region data transfer 仍計費*。Heavy write workload 月費可能 doubled。

修：

- 用 `AuroraGlobalDBReplicatedWriteIO` × per-region transfer rate 估月費
- Write-heavy workload 評估 Global Database ROI（保險、低費用版本是用 cross-region snapshot 做冷備）
- Cost 跟 RTO 一起看 — 如果接受 hours RTO、cross-region snapshot 更便宜

### Case 7：FanDuel 雙峰 case 對照（避免 over-extrapolate）

如果 team 引用 [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 規劃 multi-region 部署、要明示 scope warning。

**case「判讀」段第 1 點原文**：「直播跟投注是兩種完全不同 SLO：直播容忍秒級延遲（用 CDN + ABR 串流）、投注必須毫秒級成交。兩個服務必須各自獨立擴容、各自獨立 SLO」。

**scope warning（必明示）**：

- FanDuel 5-10x 是 *betting 服務的 Aurora 擴容倍數*、不是 streaming（streaming 走 CDN、不走 Aurora）
- 不能壓成「Aurora 撐 5-10x」單一數字
- 案例自承：betting transaction TPS 跟 concurrent streams 未公開、不能 over-extrapolate

引用 FanDuel 規劃自家 multi-region betting workload 時、看 *策略*（事件型分級 + 雙 SLO 拆分 + 多層 edge）、不套用 *具體數字*。

## 跟 Aurora DSQL / Spanner / CockroachDB 的決策樹

Global Database 是 *async + reader-only secondary*、不是 multi-region active-active。當 active-active write 是核心需求時、要看 distributed SQL 方案。

| 維度                            | Aurora Global Database            | Aurora DSQL       | Spanner            | CockroachDB            |
| ------------------------------- | --------------------------------- | ----------------- | ------------------ | ---------------------- |
| Replication                     | Async storage-level               | Sync distributed  | Sync TrueTime      | Sync Raft consensus    |
| Secondary                       | Reader-only                       | Active-active     | Active-active      | Active-active          |
| Lag                             | < 1 秒 typical                    | None (sync)       | None (sync)        | None (sync)            |
| Write                           | Primary region only               | Multi-region      | Multi-region       | Multi-region           |
| Strong consistency cross-region | No                                | Yes               | Yes                | Yes                    |
| 適用                            | DR + 跨地理 read                  | Multi-region OLTP | Global scale OLTP  | Cross-cloud OLTP       |
| 邊界                            | active-active 不支援、合規 反指標 | AWS-only、新服務  | GCP-only、學習曲線 | 跨雲、operational 複雜 |

**何時選 Global Database**：

- DR + 跨地理 read 是主要需求
- 寫流量集中在一個 region（單 region write 撐得住）
- 合規允許跨境複製（一般 SaaS、非受監管）
- 從 single-region Aurora 升級、不想換 engine

**何時改 Aurora DSQL / Spanner / CockroachDB**：

- Multi-region active-active write
- 跨 region strong consistency 是業務需求
- 跨雲 / on-prem 需求（CockroachDB）

**何時不用 Global Database**：

- 合規禁止跨境複製（Standard Chartered case）→ 每市場獨立 cluster
- Single-region 已滿足 DR / read 需求
- 跨 region cost 不划算（write-heavy workload）

## 容量與觀測

**核心 metric**：

```text
AuroraGlobalDBReplicationLag       # secondary lag、< 1 秒 typical
AuroraGlobalDBReplicatedWriteIO    # cross-region data transfer 量
AuroraGlobalDBProgressLag          # storage replication progress
```

**容量上限**：

- 1 primary region + 5 secondary region
- 每 secondary region 16 個 reader 含 1 個 headless（可升 writer）

**Cost signal**：

```text
月費 ≈ AuroraGlobalDBReplicatedWriteIO × per-region transfer rate
     + secondary region instance + storage
     + cross-region snapshot (optional)
```

Write 量大的 workload 月費可能 doubled（primary region + secondary region 都計費）、要在規劃時估準。

**驗證 DR**：

- Planned failover drill 每季一次、量測 RTO / RPO
- 受監管產業：每月一次、有合規 sign-off 記錄
- 重大版本升級前必跑一次

**回路徑**：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) cross-region cost、[8.x DR playbook](/backend/08-incident-response/) region-level failover decision。

## 邊界與整合 / 下一步

**Sibling deep articles**：

- [Aurora storage architecture](../storage-architecture/) — cross-region replication 是 storage-level 延伸
- [Aurora cross-AZ failover RTO](../cross-az-failover-rto/) — cross-AZ 跟 cross-region failover RTO 數量級對比
- [Aurora read replica scaling](../read-replica-scaling/) — fleet 治理 SSoT、合規驅動 fleet 拓樸的展開

**Migration playbook**：

- [PostgreSQL / MySQL → Aurora](../migrate-from-self-managed-pg-mysql/) — 從 PostgreSQL streaming replication 跨 region 升級的差異

**1.x 章節互引**：

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) — Global Database vs distributed SQL 對比

**何時不用本文**：single-region OLTP、無跨 region DR / read 需求時可跳過、看 [Aurora vendor overview](/backend/01-database/vendors/aurora/) 即可。

## 相關連結

- [Aurora vendor overview](/backend/01-database/vendors/aurora/) — 服務定位、適用 / 不適用場景
- [Stale Read 卡片](/backend/knowledge-cards/stale-read/) — read-after-write 容忍度
- [RPO 卡片](/backend/knowledge-cards/rpo/) — DR RPO 判讀
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 合規驅動的 Global Database anti-pattern
- [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 雙 SLO 並行的 multi-region 策略對照
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/) — 本文遵循的 6 規格面寫作模板
- 官方：[Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
