---
title: "Aurora Read Replica Scaling：15 replica 上限、lag profile、headroom 預留與 fleet 治理"
date: 2026-05-27
description: "Aurora 15 replica 上限、共享 storage 為什麼能養大量 replica、事件型容量分級表、DraftKings headroom 預留判讀、FanDuel 雙 SLO 並行、fleet 治理 3 條 driver（business sharding / microservice / 合規）"
weight: 50
tags: ["backend", "database", "aurora", "read-replica", "capacity", "fleet", "deep-article"]
---

Aurora 「最多 15 read replica」是文件數字、實際 production 部署常常更早遇到拆 cluster 的決策點 — 不是 15 replica 不夠用、是 [blast radius](/backend/knowledge-cards/blast-radius/)、業務 sharding、微服務 ownership、合規 boundary 早在 15 replica 之前就推動拆 cluster。本文同時展開兩個議題：(1) 單 cluster 內 read replica 怎麼用、容量怎麼規劃、lag 怎麼管；(2) Aurora fleet 治理的 3 條 driver、什麼條件下拆 cluster vs 加 replica。後者是 Aurora 系列的 *fleet 治理 SSoT* — [Aurora storage architecture](../storage-architecture/) / [Aurora cross-AZ failover RTO](../cross-az-failover-rto/) / [Aurora Global Database](../global-database-multi-region/) / [Aurora migration playbook](../migrate-from-self-managed-pg-mysql/) 都 cross-link 到本篇、不重複展開。

本文不是 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 而是 read replica 跟 fleet 拓樸的實作層教學。前置閱讀建議 [Aurora storage architecture](../storage-architecture/)（理解共享 storage 為什麼能養大量 replica）。

## 問題情境

典型觸發場景：FanDuel Super Bowl / DraftKings 比賽日、流量 5-10 倍尖峰、read query（用戶查 balance、投注紀錄、odds）打爆 primary、需要快速擴 read replica 但又怕 lag 把 stale read 推到 user-facing。

讀者常見的具體疑問：

- 「加 read replica 後 primary CPU 沒降、為什麼？」
- 「Auto-scaling 加 replica 要幾分鐘、來不及接尖峰怎麼辦？」
- 「Reader endpoint round-robin 把 query 打到 lag 大的 replica、用戶看到舊 balance」
- 「業務跨 200 個 cluster、單個 cluster 才 5-10 個 replica、為什麼不集中？」

進一步問題：讀寫雙峰錯位是 Aurora 讀寫分流的核心 driver。[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 揭露「write workloads spike up significantly around payout events, but opening the app during the game also activates a lot of balance queries」— 比賽進行時讀爆量、payout event 時寫爆量、兩個峰不在同一時刻。這代表 read replica 容量規劃不是「分散負載」、而是「為讀峰專門配置 capacity」。

[9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 揭露事件型容量分級：平日 baseline → 季後賽 2-3x → 季冠軍賽 4-5x → Super Bowl 5-10x。容量規劃要按事件級別分段、不是一律 10x。

對 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 這種受監管金融、不能用單一巨型 cluster — 7 個受監管市場 = 7 個獨立 cluster、合規 boundary 比運維成本優先。

## 核心機制：15 replica 上限、共享 storage、reader endpoint

Aurora read replica 的 first-class concept 是 *共享 storage + DNS-based reader endpoint*。傳統 PostgreSQL streaming replication 靠 primary push WAL 給 replica、replica 自己 apply；Aurora replica 直接從共享 storage 讀已 apply 的 page、不需要 catch-up。

**15 replica 上限**：

- 每個 Aurora cluster 最多 15 個 read replica（跨 AZ）
- 跨 region replica 走 [Aurora Global Database](../global-database-multi-region/)（不算這 15 個）
- 文件上限不是 production 真實上限 — 多數 production 部署在 5-10 replica 之間遇到拆 cluster 訊號

**共享 storage 對 lag 的影響**：

- Replica 不靠 logical replication catch-up、直接從共享 storage 讀
- Lag 來源是 *compute node 的 buffer cache 同步*、不是 WAL replay
- Typical 10-30ms、heavy write 期間可能 100ms+、但 *不會像 PostgreSQL 那樣 unbounded*

**DraftKings 揭露的「lag 可預測」frame**（[case「判讀」段第 2 點](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)）：

「30 秒降到 10-30 ms」的工程意義不只是「快」、而是「讓 read-after-write 變得可預測」。30 秒 lag 的世界裡、application 端做 read-after-write 要 cache 用戶最後寫入 30 秒以上、實務上做不到；10-30ms lag 的世界裡、application 可以做「寫操作後 100ms 內走 primary、之後可走 replica」的可規劃策略。

**Reader endpoint 行為**：

- DNS-based round-robin、不感知 replica 健康狀態
- Application 想要 lag-aware routing 要自己實作或用 RDS Proxy
- Failover 期間短暫包含 promoted replica（已升 primary）、見 [Aurora cross-AZ failover RTO](../cross-az-failover-rto/)

**Auto-scaling policy**：

- CloudWatch metric（CPU / connection）trigger
- Replica creation 2-5 分鐘
- *無法用於秒級尖峰* — 是 DraftKings「+50% no sweat」誤讀的關鍵點

**跟通用 read replica 差在哪**：Aurora replica 不用 catch-up WAL、lag 上限可預測；vs PostgreSQL streaming replication lag 是 unbounded（取決於 primary 寫速度）。可預測 lag 是 read-after-write 場景變得可規劃的前提。

對應 knowledge card：[replication-lag](/backend/knowledge-cards/replication-lag/)、[stale-read](/backend/knowledge-cards/stale-read/)。

## Step-by-step 配置 / Reader endpoint 設計

**建 read replica**：

```bash
aws rds create-db-instance \
  --db-cluster-identifier my-cluster \
  --db-instance-identifier my-replica-01 \
  --db-instance-class db.r6g.4xlarge \
  --engine aurora-postgresql \
  --availability-zone us-east-1b \
  --promotion-tier 1
```

**Reader endpoint vs Custom endpoint**：

```bash
# 預設 reader endpoint：所有 replica round-robin
# 訪問 url: my-cluster.cluster-ro-xxx.us-east-1.rds.amazonaws.com

# Custom endpoint：group 特定 replica
aws rds create-db-cluster-endpoint \
  --db-cluster-identifier my-cluster \
  --db-cluster-endpoint-identifier my-cluster-analytics \
  --endpoint-type READER \
  --static-members my-replica-analytics-01 my-replica-analytics-02
```

Custom endpoint 適用場景：

- 分析 query 走獨立 endpoint、不影響 OLTP read replica
- Read-after-write session 走 primary endpoint、其他 read 走 reader endpoint
- 不同 SLO 的 read traffic 分流（high-priority vs batch）

**Auto-scaling policy**：

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace rds \
  --resource-id cluster:my-cluster \
  --scalable-dimension rds:cluster:ReadReplicaCount \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --service-namespace rds \
  --resource-id cluster:my-cluster \
  --scalable-dimension rds:cluster:ReadReplicaCount \
  --policy-name my-cluster-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-config.json
```

**預配 vs auto-scale**：

- Peak workload 預知（賽事、促銷、季節事件）→ 提前 1 小時預配
- Unpredictable burst → auto-scale（接受 2-5 分鐘 lead time）
- 兩者混合：baseline 預配 + auto-scale 處理 baseline 之上的浮動

**驗證點**：

- `AuroraReplicaLag` < 100ms（per replica）
- Reader endpoint CPU 分布均勻（不是某 replica 過熱）
- Application stale-read error rate < 0.1%

**Rollback boundary**：移除 replica 即時生效、無 data loss；但 reader endpoint DNS cache 仍可能短暫 routing 到已移除 replica（5-30 秒）。

## 故障模式 / 邊界 case

### Case 1：加 replica 後 primary CPU 沒降

徵兆：明明加了 3 個 read replica、primary CPU 仍然 90%、reader endpoint CPU 才 10%。

原因：application 沒把 read query routing 到 reader endpoint、所有 query 仍打 primary。Aurora reader endpoint 不會自動分流 — 必須 application 端拆 read / write data source。

修：

- Application 端 ORM / data source layer 拆 read / write connection pool
- 寫操作用 writer endpoint、純讀走 reader endpoint
- 雙峰錯位是這層拆分的 driver（[DraftKings case 揭露](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 讀寫資源規劃要分開）

### Case 2：Reader endpoint round-robin 推 stale read

徵兆：read-after-write 場景（用戶下注後立刻查 balance）打到 lagging replica、看到舊 balance、客訴。

原因：reader endpoint DNS-based round-robin、不感知 lag。Application 假設 read 永遠 fresh、但 typical 10-30ms lag 期間用戶操作就會踩到。

修：

- Sticky session：寫操作後 N 秒內同 session 走 primary（N = lag p99、typical 100ms）
- Application 端做「下注後 N 秒走 primary」邏輯（DraftKings「可預測 lag」frame 讓 N 秒可規劃）
- 或用 RDS Proxy 提供 lag-aware routing（managed alternative）

### Case 3：Auto-scaling 來不及接秒級尖峰 — headroom 預留判讀

徵兆：賽事開賽 30 秒內流量 +50%、auto-scaling 觸發但 2-5 分鐘後才有新 replica、開賽尖峰已過、用戶在最關鍵時段看到 timeout。

機制限制：replica creation 2-5 分鐘、秒級尖峰過去了 replica 才上線。

**DraftKings「Super Bowl +50% no sweat」的工程意義**（[case「判讀」段第 3 點原文](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)）：「這句話的工程意義是 *提前做好容量規劃*、不是『Aurora 神奇』。寫 workload 預期可能 +50%、整個 system headroom 預留至少 50%、加上 read replica 動態加減、才能讓 50% 增幅變成『不流汗』」。

工程含義：

- Peak workload 預知（賽事 / 促銷）用 *headroom 預留 + [scheduled scaling](/backend/knowledge-cards/scheduled-scaling/) 提前預配*、不靠 auto-scale 接秒級
- Auto-scale 是 unpredictable burst 才用（突發新聞、KOL 推廣、未預期事件）
- DraftKings 的「不流汗」是 *系統設計* 結果、不是 Aurora 特殊能力

修：

- 賽事日曆建模：賽前 1 小時自動加 replica、賽後 2 小時減
- Primary instance class 升級提前一週、不是賽前升（升級期間 failover 風險）
- Headroom 預算：read replica 預留 50%、primary CPU baseline < 50%

### Case 4：15 replica 上限 — 拆 cluster 訊號

徵兆：read traffic 持續成長、加到 15 replica 仍接近 CPU 瓶頸、想加第 16 個被 API 拒絕。

原因：Aurora 硬上限 15 replica / cluster、超過要拆 cluster。但實務上更常在 5-10 replica 就遇到其他拆 cluster 訊號（blast radius、ownership boundary、業務 sharding）。

修：見下方「邊界與整合：fleet 治理 SSoT」段、按 3 條 driver 判讀拆 cluster vs 加 replica。

### Case 5：Heavy write 期間 replica lag spike

徵兆：bulk insert / DDL 期間 replica lag 從 10-30ms 跳到 100-500ms、application 假設 typical lag 永遠成立、stale read 比例大幅上升。

原因：heavy write 期間 replica buffer cache invalidate 速度跟不上、lag 暫時拉大。Aurora 的「可預測 lag」不等於「lag 永遠 10-30ms」。

修：

- bulk insert / DDL 期間 application 端切到全 primary 模式（避開 stale read 風險）
- 重要 DDL 用 [pg_repack](https://github.com/reorg/pg_repack) 或 logical migration、避免長時間 table lock
- 監測 `AuroraReplicaLagMaximum`、spike 超過 p99 threshold trigger application 端 fallback

### Case 6：FanDuel 雙 SLO 並行 — 不要壓成單一數字

徵兆：team 看 FanDuel「5-10x peak」直接套到自家 streaming workload、結果 Aurora 撐不住、發現 FanDuel streaming 根本不走 Aurora。

[9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) case「判讀」段第 1 點原文：「直播跟投注是兩種完全不同 SLO：直播容忍秒級延遲（用 CDN + ABR 串流）、投注必須毫秒級成交。兩個服務必須各自獨立擴容、各自獨立 SLO」。

**scope warning（必明示）**：

- FanDuel 5-10x 是 *betting 服務的 Aurora 擴容倍數*、不是 streaming
- Streaming 走 CDN、不走 Aurora
- 不能把兩種 SLO 壓縮成「Aurora 撐 5-10x」單一數字

**case 自承的進一步 scope warning**：「AWS 案例 *沒有* 提具體 betting transaction TPS、concurrent streams、延遲分布」（case「需要警惕」段）。引用 FanDuel 時不能寫「Aurora 在 betting 路徑撐 X TPS」這類細節 — case 沒提的數字不能擴寫。

修：

- 不同 SLO workload 拆獨立 cluster 或拆 read / write data source
- 容量規劃看自家 workload TPS、不要套用未公開的 case 數字

## 事件型容量分級表

[9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 揭露事件型 scaling 不是一律 10x — *事件級別* 是容量分級單位：

| 事件級別              | 倍數  | 來源                          |
| --------------------- | ----- | ----------------------------- |
| 平日 baseline         | 1x    | FanDuel case「判讀」段第 3 點 |
| 季後賽 playoff        | 2-3x  | FanDuel case 揭露事件分級     |
| 季冠軍賽 championship | 4-5x  | FanDuel case 揭露事件分級     |
| Super Bowl            | 5-10x | FanDuel case 揭露事件分級     |

**Frame 8 event-driven scaling 5 模式（跨 vendor 共寫）**：本表是 Aurora 端從讀峰視角切入的事件分級、跟 [DynamoDB on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) 的 5 模式分類（flash-sale spike / predictable peak / sustained growth / surge baseline permanent shift / B2B sustained + 高可用）共軸。Aurora 端的 FanDuel 季賽 cycle 在 5 模式分類中對應 *predictable peak* 的時間序列展開 — 事件 tier 已知（賽季 → 季後賽 → 季冠軍賽 → Super Bowl）、按 tier 預配 read replica 數量、本質是「峰值已知 + 重複出現」的 predictable peak 在多 tier 結構下的延伸。

**KV 層 vs SQL 層的 mode 決策差異**：DynamoDB 端的 on-demand vs provisioned mode 是 KV vendor 的容量抽象（軸 1 peak/avg ratio / 軸 4 predictable-peak vs flash-sale）、詳見 [DynamoDB on-demand-vs-provisioned 6 軸決策](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)、本篇不展開。Aurora 端對應的決策是 *read replica 數量 + auto-scaling vs scheduled scaling vs headroom 預留*、靠的是 replica fleet size 而非 mode 切換。

兩 vendor 在 Frame 8 各自承擔：

- **DynamoDB on-demand-vs-provisioned**：5 模式分類 SSoT、mode × 事件型分類的合成判讀
- **Aurora read-replica-scaling（本篇）**：read 峰值的 headroom 預留 + 雙 SLO 並行（FanDuel 分級 + DraftKings 讀寫雙峰錯位）+ fleet 治理

**case 自帶警示（scope warning 必保留）**：

- 「5-10x」是 *峰值倍數*、不是 *peak 持續時間*。Super Bowl 的關鍵 30 分鐘可能 8-10x、其他 3 小時可能 3-5x（case「需要警惕」段）
- 分級 driver 是「同類事件中的最高倍率」、不是恆定數字 — 引用時要保留事件 tier 對應、不是一律「Super Bowl = 10x」單一閾值
- 跨業務 transfer 判讀：本表 *只代表體育博彩賽季 cycle*、不能直接套到 e-commerce flash-sale（後者倍數結構是「秒級數千倍」、跟事件 tier 結構不同）

**容量規劃做法**：

- 建立 event tier 體系、每 tier 對應不同 pre-scale 倍數跟 lead time（賽前 N 小時預配）
- 事件型分級的關鍵是「峰值是已知的」、不是「峰值多大」
- 對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 的容量分級

## 邊界與整合：Fleet 治理 SSoT — 何時拆 cluster vs 加 replica

本段是 Aurora fleet 治理軸 SSoT — [Aurora storage architecture](../storage-architecture/) / [Aurora cross-AZ failover RTO](../cross-az-failover-rto/) / [Aurora Global Database](../global-database-multi-region/) / [Aurora migration playbook](../migrate-from-self-managed-pg-mysql/) cross-link 不重複展開。

**跨 case 合成 frame**：production scale 不是「單一巨型 cluster」而是 *fleet of clusters*、但 *driver 各異*。

| Driver                 | Case anchor                                                                                           | Fleet 規模  | 拆分判讀                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| Business sharding      | [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)         | 200 cluster | 業務本身可切分（每體育類別 / 每地理 / 每產品線各自 cluster）、blast radius 隔離      |
| Microservice ownership | [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)                 | 多 cluster  | 每微服務私有 store、不共用 cluster — 容量規劃分散到 service owner                    |
| 合規市場 boundary      | [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 7 cluster   | 受監管市場資料 *不能跨境複製*、每市場獨立 cluster — Global Database 在合規場景反指標 |

### Driver 1：Business sharding（DraftKings 200 cluster）

DraftKings 不用一個巨型 cluster 撐 100 萬 ops/min、而是 *按業務切 200 cluster*。每體育類別、每地理、每產品線各自 cluster、blast radius 自然隔離。

工程含義：

- 業務本身就有 sharding key（sport type / region / product line）— 拆 cluster 不需要 schema redesign
- 單 cluster 故障只影響該業務、不影響全平台
- 容量規劃變成「每 cluster 的容量規劃」、單機極限不重要

**容易誤判的邊界**：[DraftKings 100 萬 ops/min ≈ 17K ops/sec](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 是 *200 cluster 加總*、平均每 cluster 約 80 ops/sec（case「需要警惕」段）— 不是「單一 cluster 撐 100 萬 ops」、案例對照不能擴寫成單 cluster 容量。

### Driver 2：Microservice ownership（Netflix）

Netflix 每微服務各自有 private Aurora cluster、不共用 — 跟 monolith「一個大 DB 撐全部」相反。

工程含義：

- DB 容量規劃變成「每微服務的容量規劃」、複雜度分散到 service owner
- 跨服務 contention 變成 *network 議題* 而非 *DB lock 議題*
- 每多一個微服務就多一個 cluster、operational surface area × N

**case 自帶 scope 警示**：[Netflix 數據層遠不止 Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 還有 Cassandra（playback metadata）、EVCache（cache layer）、Iceberg（data warehouse）。Aurora 主要是「需要 ACID 的 OLTP 工作負載」、不是「all-purpose store」（case「需要警惕」段第 2 點）。讀者引用 Netflix consolidation 時、不能誤推論「Aurora 可以替所有 store」。

### Driver 3：合規市場 boundary（Standard Chartered 7 cluster）

Standard Chartered 7 個受監管市場 = 7 個獨立 cluster。[Data Residency](/backend/knowledge-cards/data-residency/) 規範資料 *不能跨境複製*、[Aurora Global Database](../global-database-multi-region/) 在這種場景違反合規。

工程含義：

- 容量規劃變成「7 個獨立規劃 × 各自合規門檻」
- 跨市場 DR 不靠 Global Database、靠應用層市場切換
- 合規 lead time 是時程主項（見 [migration playbook](../migrate-from-self-managed-pg-mysql/) 合規時程段）

**case 自承 scope 警示**：Standard Chartered case 未公開是 PostgreSQL 還是 MySQL、未公開具體 cost 數字、屬「相關 case study」匿名對照。

### 何時拆 vs 加 replica 的判讀順序

按以下順序判斷、第一個成立的就是拆 cluster 的訊號：

1. **> 15 replica 需求** → 拆 cluster（Aurora 硬上限）
2. **Blast radius 隔離需求** → 拆 cluster（單 cluster 故障影響範圍太大、業務不能接受）
3. **業務本身可切分**（user shard / 產品線 / 地理）→ 拆 cluster（DraftKings 拓樸）
4. **微服務私有 store 拓樸** → 拆 cluster（Netflix 拓樸、跟服務生命週期綁定）
5. **合規禁止跨境複製** → 拆 cluster（Standard Chartered 拓樸、Global Database 反指標）
6. **以上都不成立** → 加 replica（最便宜的容量槓桿）

**容易誤判的邊界**：

- Fleet 治理本身有 ops surface area 成本（parameter group / backup / IAM / observability fan-out × N cluster）— 不是免費；driver 不夠強時不該拆
- 「fleet 看起來大」不是 driver — driver 是業務本身有 boundary、不是運維美觀
- 拆 cluster 後再合併比拆更難（資料遷移成本高）— driver 不確定時先加 replica

## 容量與觀測

**核心 metric**：

```text
AuroraReplicaLag           # per replica lag
AuroraReplicaLagMaximum    # cluster max lag
CPUUtilization             # per replica CPU
DatabaseConnections        # per replica connection
```

**Application 端 metric**：

```text
read_query_latency_p99       # per endpoint (writer vs reader)
stale_read_error_count       # read-after-write 失敗訊號
read_replica_routing_ratio   # writer vs reader 流量比例
```

**容量上限**：

- 15 replica / cluster（硬上限）
- Cross-region replica 走 [Aurora Global Database](../global-database-multi-region/)（不算 15）

**容量公式**：

```text
read replica count = (read QPS / replica throughput) × (1 + lag buffer) × (1 + event tier headroom)

lag buffer        = 30%（典型）
event tier headroom = 0% (平日) / 50% (playoff) / 100% (championship) / 200% (Super Bowl)
```

**回路徑**：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 read-bound vs write-bound、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) peak workload 預配 vs auto-scale 決策。

## 邊界與整合 / 下一步

**Sibling deep articles**：

- [Aurora storage architecture](../storage-architecture/) — 共享 storage 為什麼能養 15 replica + 雙峰錯位 application 邊界
- [Aurora cross-AZ failover RTO](../cross-az-failover-rto/) — replica 升 primary 流程
- [Aurora Global Database](../global-database-multi-region/) — 跨 region replica 配置 + 合規 anti-pattern

**Migration playbook**：

- [PostgreSQL / MySQL → Aurora](../migrate-from-self-managed-pg-mysql/) — fleet 拓樸是 migration 規劃的維度之一

**1.x 章節互引**：

- [1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) — read replica 是 OLTP 擴容的基本槓桿

**RDS Proxy 整合**：lag-aware routing、connection pool 共享、Lambda 場景；managed alternative。

**何時不用本文**：single replica + cross-AZ failover 已滿足、read traffic 不是 bottleneck 時可跳過、看 [Aurora vendor overview](/backend/01-database/vendors/aurora/) 即可。

## 相關連結

- [Aurora vendor overview](/backend/01-database/vendors/aurora/) — 服務定位、適用 / 不適用場景
- [Replication Lag 卡片](/backend/knowledge-cards/replication-lag/) — 概念基底
- [Stale Read 卡片](/backend/knowledge-cards/stale-read/) — read-after-write 容忍度
- [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 200 cluster business sharding 跟 headroom 預留
- [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 微服務私有 store + Aurora 非 all-purpose store 邊界
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 合規驅動 fleet 拓樸
- [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 雙 SLO 並行 + 事件型容量分級
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/) — 本文遵循的 6 規格面寫作模板
- 官方：[Aurora replication](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Replication.html)
