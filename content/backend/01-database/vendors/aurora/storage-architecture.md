---
title: "Aurora Storage Architecture：quorum-based 分散式 log 與韌性即性能設計"
date: 2026-05-27
description: "Aurora storage / compute 分離、6-way 跨 AZ replication、4-of-6 write / 3-of-6 read quorum、韌性投資自動 amortize 成 read 性能、DraftKings 6ms 寫 / <1ms 讀 production reference"
weight: 30
tags: ["backend", "database", "aurora", "storage", "quorum", "replication", "deep-article"]
---

Aurora 把 storage 從「block device + WAL on local disk」重寫成跨 AZ 分散式 log service、compute node 只負責 process query 跟 generate redo log records。這個設計直接決定 read replica、failover、backup 跟跨 AZ replication 的物理上限 — 不理解 storage layer 設計、就無法解釋為什麼 [9.C23 Netflix consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 拿到 +75% 效能、為什麼 [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) replication lag 從 30 秒降到 10-30ms、為什麼 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 能同時把韌性跟性能當成單一目標。

本文不是 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 而是 storage-level 設計的實作層教學。覆蓋 quorum-based replication 的工程含義、「韌性即性能」frame 為什麼成立、OLTP workload 在 storage 設計下的讀寫雙峰錯位、跟容量規劃的判讀槓桿。

## 問題情境

典型觸發場景：團隊從 RDS PostgreSQL / 自管 PostgreSQL 遷到 Aurora、看到「跨 AZ replication lag 從秒級降到毫秒級」、但讀文件「quorum」「4-of-6」「分散式 storage」訊息密集、不知道哪些設計決策要相信、哪些是 marketing 詞。

讀者常見的具體疑問：

- 「為什麼 Aurora 寫入比 RDS 還低、不是該因為跨 AZ network round-trip 而變慢？」
- 「Storage layer 跟 compute layer 分離具體怎麼影響 backup、failover 跟 read replica？」
- 「6 個 storage node 失去 2 個還能寫嗎？失去 3 個呢？」
- 「Aurora 文件講『韌性』跟『性能』都用 storage 設計解釋、是同一件事還是兩件事？」

進一步問題：傳統工程文化把可靠性跟性能視為對立 — HA 投資（跨 AZ replication、failover 演練）通常被當成性能成本、不被視為性能來源。Aurora 設計反這個直覺、但讀者需要看到具體機制才能信。Standard Chartered case 揭露這個 frame 在受監管銀行業務（要求兩者同時達標）的價值；DraftKings 揭露具體數字（讀 < 1ms、寫 6ms）。

## 核心機制：quorum-based 分散式 log

Aurora storage 的 first-class concept 是 *quorum 寫入 + 6-way 跨 AZ replication*。傳統 PostgreSQL primary 把 storage 跟 CPU / RAM 綁定、storage 擴容要換 instance、replication 在 compute 層做（streaming replication、logical replication）。Aurora 把 storage 拉到分散式 log service、6 個 storage node 各自獨立、application 看到的仍是 single primary SQL。

**Storage layout**：每個 storage segment 跨 3 AZ × 2 node、共 6 個 storage node。一個 cluster 的 storage 被切成多個 10GB segment、每個 segment 6-way 複製。

**Quorum 設定**：

- Write quorum：4-of-6（4 個 storage node 確認寫入才算 commit）— 容忍 1 AZ 失效 + 1 node 失效仍能寫
- Read quorum：3-of-6（讀 3 個 node 取最新版本）— 比 write 小、降低 read latency
- 算術不對稱：寫嚴讀鬆是設計選擇、不是 marketing — durability 由寫端保證、讀端可以放寬

**Write path 跟傳統 PostgreSQL 的差異**：

- PostgreSQL primary：寫 WAL 到 local disk + dirty page flush + 透過 streaming replication 推到 replica
- Aurora compute node：只送 *redo log records* 到 storage、不送整個 page；storage node 自己 apply redo log 重建 page、自己 checkpoint、自己 backup
- 工程含義：compute node 寫量小、CPU 不被 dirty page flush 佔用、寫入路徑變短

**「韌性即性能」frame**（[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 揭露）：

Aurora 把 HA 從 application-level（Patroni promotion + WAL catch-up）下推到 storage-level。設計含義是：storage 投資（6-way 跨 AZ replication）自動成為 read replica 的容量基底 — read replica 不需要 catch-up WAL、直接從共享 storage 讀、HA 預算同步轉成讀分流預算。

對 Standard Chartered 受監管銀行業務這代表：合規要求的 RPO / RTO 不能放棄、但業務也要求每秒 4000 TPS、兩者必須同時達成。傳統路徑要分別投資 HA（複雜的 streaming replication topology）跟性能（read replica catch-up tuning）、且兩個投資互相干擾。Aurora 讓 *同一份 storage 投資* 同時提供兩件事 — case「判讀」段第 2 點原話：「Aurora 的多 AZ storage + replica 同時提供性能（讀分流）跟韌性（故障切換）、達成 *韌性即性能* 的目標」。

對應 knowledge card：[quorum](/backend/knowledge-cards/quorum/)、[replication-lag](/backend/knowledge-cards/replication-lag/)。

**跟通用 quorum 概念差在哪**：Aurora quorum 是 *storage-level*（不是 application-level Cassandra 風格）、application 看到 single primary SQL、不用感知 quorum；vs Cassandra application 要選 consistency level（ONE / QUORUM / ALL）。

## OLTP workload shape：讀寫雙峰錯位

Aurora 設計的工程含義在 application 層落地時、要看 workload 形狀。[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 揭露一個 OLTP 容量規劃的典型 pattern。

**DraftKings 揭露的雙峰錯位**（case「觀察」段最後一行原文）：「write workloads spike up significantly around payout events, but opening the app during the game also activates a lot of balance queries」— 比賽進行時是讀爆量（balance query）、payout event 時是寫爆量（ledger write）、兩個峰不在同一時刻。

**工程含義**：

- 讀寫資源規劃要分開、不能用「峰值總 TPS」單一數字規劃容量
- 讀峰拉 read replica 容量、寫峰靠 primary instance class 跟 commit batching、兩條路徑獨立預配
- 預估 headroom 也要分開：讀的 headroom 可以靠 auto-scale replica 接、寫的 headroom 要靠 primary 提前升 instance class（不能 auto-scale）

**Application-level boundary**：雙峰錯位是 *application 層* 拆讀寫 datasource 的決策訊號、storage layer 本身不解。Aurora 共享 storage 提供 lag 上限可預測（10-30ms）— 這是 read replica 變成「production-grade 可用」的前提、但讀寫分流要 application 端拆 read / write data source 才能落地。Storage 設計給的是「可預測的 lag 上限」、不是「自動讀寫分離」。

**跨 case 對照**：

[9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 揭露另一種雙峰 — 直播 + 投注 *兩種服務* 同時峰、不是同服務讀寫錯位。這兩種雙峰類型要分清楚：

- 同服務讀寫錯位（DraftKings）：解法是 read / write data source 拆分、共享 Aurora cluster
- 跨服務雙峰（FanDuel）：解法是不同服務各自獨立擴容、betting 走 Aurora、streaming 走 CDN

雙峰類型不同、容量規劃策略不同。

## Step-by-step 配置 / 觀測

Aurora storage 是 cluster-level、不暴露 segment-level config。讀者能影響的維度是 instance class、storage type、backup retention 跟 monitoring。

**Cluster 建立**：

```bash
aws rds create-db-cluster \
  --db-cluster-identifier my-cluster \
  --engine aurora-postgresql \
  --engine-version 15.5 \
  --master-username admin \
  --master-user-password "$(aws secretsmanager get-secret-value --secret-id db-password --query SecretString --output text)" \
  --storage-type aurora-iopt1 \
  --backup-retention-period 7
```

關鍵欄位：

- `--storage-type aurora-iopt1`：Aurora I/O-Optimized、月費高 30% 但無 I/O 收費；write-heavy + scan-heavy workload 才划算
- `--storage-type aurora`（預設）：Standard storage、按 I/O 計費；read-light workload 划算
- `--backup-retention-period 7`：1-35 天、影響 PITR 範圍

**觀測 storage 狀態**：

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier my-cluster \
  --query 'DBClusters[0].{StorageType:StorageType,AllocatedStorage:AllocatedStorage,Status:Status}'
```

**CloudWatch metric**（cluster-level）：

```text
VolumeBytesUsed           # 當前 storage 用量、接近 128 TB 上限要警告
VolumeReadIOPs            # storage 層讀 IOPS、判斷 I/O-Optimized ROI
VolumeWriteIOPs           # storage 層寫 IOPS、跟 compute 層 WriteIOPS 對照
AuroraVolumeBytesLeftTotal # 剩餘可用 storage
```

**Performance Insights wait event**：

```text
db.IO.aurora_redo_log_flush   # quorum write 等待訊號、p99 > 10ms 要看
db.IO.aurora_storage_xx       # storage layer I/O 細節
```

**驗證點**：

- 寫入 latency p99：PostgreSQL primary 1-3ms vs Aurora 3-6ms、跨 AZ network round-trip 是物理下界
- Read latency p99：Aurora < 1ms（從共享 storage 讀、不跨 AZ）
- Storage autoscale event：128 TB 上限前自動 grow per 10GB

**Rollback boundary**：Aurora storage 是 cluster-level、無法回滾 storage 設計；唯一 rollback 是切回 RDS / 自管（走 migration playbook、不是配置層 rollback）。

## 故障模式 / 邊界 case

### Case 1：誤以為 Aurora 寫入一定比 PostgreSQL primary 快

徵兆：團隊期待 Aurora 寫入比自管 PostgreSQL 快、實測 p99 寫入 latency 沒明顯改善、甚至小 row + 單筆 commit 場景 Aurora 反而慢。

原因：跨 AZ network round-trip 是 3-5ms 物理下界、4-of-6 quorum 至少要等 4 個 storage node ack、單筆小寫場景 local SSD primary 仍有 latency 優勢。Aurora 的寫入優勢在 *壓力下* 才顯現 — write throughput 高峰時 PostgreSQL primary 受限於 dirty page flush + WAL fsync + replica catch-up、Aurora 的 storage layer 各自獨立處理 redo log apply。

> **數字口徑**：「跨 AZ round-trip 3-5ms」屬通用工程估算（光速下界 + AWS 區內 AZ 物理距離）、case 未直接量化、實際值依 region / AZ pair / instance 類型而異、要看 AWS 官方 latency table 或自家 benchmark 校正。下方 DraftKings 6ms 寫入是 case 揭露的 production reference、可作為對照基線。

修：

- benchmark 要跑壓力測試、不能只測單筆 latency
- 寫入 latency 不是 Aurora 的核心賣點、是 *可預測的 read replica lag + 韌性* 才是
- DraftKings 6ms 寫入是 production reference：跨 AZ quorum 的物理下界、不是 Aurora 慢

### Case 2：AZ-level outage 期間寫入 latency spike

徵兆：1 個 AZ 失效後、寫入 p99 從 6ms spike 到 30-50ms、application timeout 增加。

原因：失去 1 AZ 後 quorum 仍成立（4-of-6 → 用剩 4 個 node 寫）、但 storage node fault 期間需要等 timeout 才確認；單一 storage node 額外 fault 會把寫推到 timeout。Aurora 在 AZ outage 期間 *能寫*、但不是 *性能不變*。

修：

- 監測 `AuroraVolumeBytesLeftTotal` 跟 storage IOPS 分布、AZ outage 期間自動切到剩餘 AZ
- application 端做 retry + circuit breaker、不要假設寫入永遠 6ms
- 確認 cluster 至少跨 3 AZ deploy、單 AZ outage 才有 quorum 餘地

### Case 3：I/O-Optimized 費用誤判

徵兆：team 看 Aurora I/O-Optimized「無 I/O 收費」直接切過去、月帳變高 25%、沒看到 ROI。

原因：Standard storage 按 I/O 收費、I/O-Optimized 月費比 Standard 高 30%。只有 *write-heavy + scan-heavy* workload（I/O 月費接近 instance 費用）才划算；read-light + write-light workload 反而吃虧。

修：

- 先量測 baseline I/O：`VolumeReadIOPs + VolumeWriteIOPs × $0.20 per million I/O` vs Standard 月費
- I/O 費用 > instance 費用 30% 才切 I/O-Optimized
- DraftKings 用 I/O-Optimized 是因為金融帳本 write-heavy + balance query scan-heavy、ROI 明顯

### Case 4：Storage autoscale 假設

徵兆：TRUNCATE / DROP 大表釋放 50% storage、但下月帳單沒回落。

原因：Aurora storage 自動 grow、但 *不自動 shrink*。已分配的 storage 持續計費、TRUNCATE / DROP 只釋放 logical space、physical storage 仍占用。要 shrink 必須走 logical migration（dump / restore 到新 cluster）。

修：

- 大量 DROP 操作前先評估是否值得做 logical migration
- 用 partition + DETACH 而非 DROP TABLE、partition 可以單獨 archive
- 接受 storage 用量是 *peak watermark* 而非 *current usage*

### Case 5：Replication lag 誤解

徵兆：read replica lag 10-30ms 看起來夠快、application 假設 read-after-write consistency、用戶下注後立刻查 balance 偶發看到舊資料。

原因：10-30ms 是 *typical*、heavy write + slow query 期間可能秒級。Aurora 共享 storage 設計讓 lag *可預測*（不會像 PostgreSQL streaming replication unbounded）、但 *可預測* 不等於 *zero*。Read-after-write 場景仍需要 application 端處理。

修：

- 用戶寫操作後 N 秒內走 primary（N 由 lag p99 決定、典型 100ms）
- Aurora 提供 session pinning：寫完同 session 短期內走 primary
- 不能假設「Aurora replication lag 小到可以忽略」、要看 application 容忍度

## 容量與觀測

**核心 metric**：

```text
VolumeBytesUsed           # storage 用量、128 TB 上限預警
AuroraReplicaLag          # replica lag、判斷讀寫分流可行性
db.IO.aurora_redo_log_flush # quorum write 等待、storage 瓶頸訊號
```

**Production reference number**（[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 揭露、case「觀察」段表格）：

| 指標            | DraftKings 在 Aurora MySQL 的數字 |
| --------------- | --------------------------------- |
| 讀延遲          | < 1 ms                            |
| 寫延遲          | 6 ms                              |
| Replication lag | 從 30 秒降到 10-30 ms             |

這個 production reference 取代用「typical 3-5ms」籠統說法。讀寫 6x 差距是 OLTP 容量規劃槓桿 baseline — 寫延遲是 quorum 4-of-6 + 跨 AZ network round-trip 的物理下界、不是 storage 設計能再壓低。引用時要明示是 DraftKings production reference、不是 Aurora marketing。

**容量上限**：

- 128 TB / cluster（超過要拆 cluster、見 [Aurora read replica scaling](../read-replica-scaling/) fleet 治理 SSoT）
- 15 read replica / region（[Aurora read replica scaling](../read-replica-scaling/) 展開）
- Storage 自動 grow per 10GB

**跨 region replication**：[Aurora Global Database](../global-database-multi-region/) 用 `AuroraGlobalDBReplicationLag` 監測、< 1 秒 typical。

**回路徑**：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 抽 CloudWatch evidence、[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 storage-bound vs compute-bound。

## Netflix +75% 效能改善的根因

[9.C23 Netflix consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 案例揭露 storage 設計的具體效能含義。Netflix 把多套 RDBMS（PostgreSQL / MySQL / Oracle）統一到 Aurora、拿到 *up to 75%* 效能改善、-28% 成本。

**+75% 的根因**：

- 傳統 PostgreSQL primary 寫 WAL + dirty page flush + 透過 streaming replication 推到 replica
- Compute 大量 CPU 用在 dirty page flush + replication encoding、不是用在 query processing
- Aurora compute 只送 redo log records、storage 自己 apply page、自己 checkpoint
- → 同樣 instance class 下、Aurora compute 能處理更多 query

這不是 marketing 的「分散式儲存讓效能提升」籠統說法、而是具體的 *compute 不再 flush dirty page*。

**scope warning（必明示、case 自帶警示原話）**：

「effective 75% improvement 是跨多 workload 的最大改善幅度、不是『每個 workload 都 +75%』。實際每個 workload 改善幅度從 10% 到 75% 不等」（case「需要警惕」段第 1 點）。

引用 Netflix 時不能把 75% 套到單一 workload — 容量規劃要看自家 workload 形狀（write-heavy / read-heavy / scan-heavy）、預估改善幅度範圍而非單一數字。

## Fleet 治理（cross-link、不展開）

Production scale 不是「單一巨型 Aurora cluster」而是 *fleet of clusters* — 5 case 揭露同一 frame：

- DraftKings 200 個獨立 cluster（按業務切分）
- Netflix 多 cluster（微服務私有 store）
- Standard Chartered 7 個 cluster（受監管市場 boundary）

跨 case 合成的 fleet 拓樸 3 條 driver（business sharding / microservice ownership / 合規市場 boundary）跟「何時拆 cluster vs 加 replica」的判讀順序、SSoT 在 [Aurora read replica scaling](../read-replica-scaling/) 邊界段。Storage 設計本身不解 fleet 邊界決策 — Aurora 解 single-cluster scaling（quorum / 共享 storage / 共享 backup）、但「拆幾個 cluster」是業務拓樸決策。

## 邊界與整合 / 下一步

**Sibling deep articles**：

- [Aurora cross-AZ failover RTO](../cross-az-failover-rto/) — storage 設計如何加速 failover（replica 不需要 catch-up）
- [Aurora read replica scaling](../read-replica-scaling/) — 共享 storage 為什麼能養 15 replica + fleet 治理 SSoT
- [Aurora Global Database](../global-database-multi-region/) — 跨 region storage replication 設計

**Migration playbook**：

- [PostgreSQL / MySQL → Aurora](../migrate-from-self-managed-pg-mysql/) — storage 設計差是 operational redesign 的核心 driver

**1.x 章節互引**：

- [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) — quorum 寫入 vs single-primary transaction 邊界
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) — Aurora storage 是 single-region scaling、不是 distributed SQL

**何時不用本文**：single-region OLTP 用 RDS 仍足夠、storage architecture 細節不影響容量規劃時可跳過、看 [Aurora vendor overview](/backend/01-database/vendors/aurora/) 即可。

## 相關連結

- [Aurora vendor overview](/backend/01-database/vendors/aurora/) — 服務定位、適用 / 不適用場景
- [Quorum 卡片](/backend/knowledge-cards/quorum/) — 概念基底
- [Replication Lag 卡片](/backend/knowledge-cards/replication-lag/) — 對照通用 replication lag 模型
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/) — 本文遵循的 6 規格面寫作模板
- 官方：[Aurora storage architecture](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.StorageReliability.html)
