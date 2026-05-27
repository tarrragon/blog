---
title: "Spanner TrueTime API 深度：GPS + 原子鐘、commit wait、為什麼 line-rate scaling 才是設計目的"
date: 2026-05-27
description: "TrueTime 是手段、line-rate scaling 才是 Spanner 的設計目的。本文先扣商業邏輯：傳統 OLTP coordinator 為什麼是 bottleneck、Spanner 怎麼用 TrueTime + Paxos 換成拓樸感知多 leader；再展開 TrueTime ε / commit wait 數學、ε 暴衝失敗模式、cross-region voting 對 latency 的影響、跟 9.C10 Google internal dogfood 揭露的線性擴展模式對照"
weight: 30
tags: ["backend", "database", "spanner", "global-sql", "truetime", "external-consistency", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 implementation-layer deep article。Overview 已說明 Spanner 在全球 OLTP 譜系的定位、本文聚焦 *TrueTime API* — Spanner 用來消滅 single coordinator bottleneck、換到 line-rate scaling 的核心機制。

---

## 商業邏輯先行：TrueTime 是手段、line-rate scaling 才是目的

TrueTime 的設計目的是消滅 single coordinator bottleneck、讓 OLTP 拿到 line-rate scaling — external consistency 只是這條路徑上拿到的副產品。讀者若把 TrueTime 當成「一個保證 external consistency 的精巧時間 trick」、會誤把工具當目標、後續所有 commit wait / Paxos / GPS 細節都解錯方向。

傳統 OLTP（PostgreSQL、MySQL、Cloud SQL）跨節點交易要靠一個 coordinator 決定全局順序、coordinator 本身就是 bottleneck。`1x node = 1x throughput` 的線性擴展在 single-primary 模型撞牆、想 scale 只能往應用層 sharding 走、付管理 shard key / 跨 shard query / resharding 的代價。Spanner 換掉這條路徑：TrueTime 把 wall-clock 變成跨 datacenter 可比較的 *interval*、Paxos 把 coordinator 變成「拓樸感知的多 leader」（每個 [Range Sharding](/backend/knowledge-cards/range-sharding/) split 自己的 Paxos group 各自前進）、commit timestamp 用 TrueTime 對齊到 real-time 順序、不再需要一個全局 coordinator 串行所有 transaction。

9.C10 Cloud Spanner planetary scale case 揭露的線性擴展證據：「2 nodes → 45K reads/sec、4 nodes → 90K reads/sec」是 Spanner 設計目標的直接證據、不只是 marketing 數字。這條揭露 Spanner external consistency 不是「加強版 serializable isolation」、是「coordinator 換拓樸」的 paradigm shift。寫到這裡讀者該意識到一件事：選 Spanner 不是選一個更貴更強的 SQL、是選一條 *把 coordinator 拆掉* 的 scaling 路徑。

**Dogfood 邊界（本文反覆強調）**：9.C10 是 Google internal dogfood case、不是 customer-facing capacity 參考。「10 億 req/sec」是 Google 全使用者加總、不是單一 instance 配額；「2 nodes → 45K reads / 4 nodes → 90K reads」是 Google internal benchmark 揭露的線性擴展 *模式*、不是客戶 SLA 承諾。本文後續所有 9.C10 數字引用都會明示這條邊界、避免讀者誤把 dogfood 當配額。

**Fact vs derive 分層警告**：本段「coordinator bottleneck → TrueTime + Paxos」frame 是跨 Spanner 2012 OSDI 論文 + 公開文件（2024-2026）+ 9.C10 case 合成的工程 frame、不是 9.C10 case 直接展開實作層細節。9.C10 案例直接揭露的 fact 是線性擴展數字跟 dogfood 邊界；本文 derive 的 frame 是「為什麼傳統 OLTP coordinator 是 bottleneck」。引用時這條分層在每段引用具體數字時都會重申。

## 問題情境：跨 region OLTP 的順序漏洞

跨 region OLTP 想保證「全球用戶看到的交易順序跟 wall clock 一致」、但 NTP 同步誤差動輒 10-100ms、足夠讓 region A 已 commit 的計費事件被 region B 看到一個更新的 timestamp 卻是舊狀態。讀者徵兆通常從這幾個地方浮現：分散式系統團隊在 Cloud SQL / Aurora 多 region 上做 read replica、發現「跨 region read 順序顛倒」、audit log timestamp 不可靠、reconcile 對帳對不上、業務以為自己用了 transaction 就有「強一致」、實際只有 single-node 的 serializable isolation。

真實壓力場景：Google Ads 計費需要把每筆扣款事件放進可驗證的 *外部* 順序、不只是 transaction 內部 serializable。讀者若把這套需求帶回自家系統、會發現一條共同訊號 — 「兩個 transaction 都 commit 成功、用戶體感卻違反順序」這種事故、不是 isolation level 的問題、是 *external consistency* 的問題。

Case anchor：[9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads / Play 訂閱 / Search 計費跟 TrueTime 綁定。**dogfood 邊界明示**：9.C10 是 Google 內部 dogfood case、不是 customer-facing capacity 參考；引用其揭露的線性 scaling 模式時要分清「設計目標證據」vs「客戶可獲得配額」。

## 核心機制：TrueTime 的 API 跟硬體基礎

TrueTime 對外只有兩個 primitive — `TT.now()` 回傳一個 *interval* `[earliest, latest]`、不是單一時刻；`TT.after(t)` / `TT.before(t)` 判斷一個事件是否確定在 t 之後 / 之前。整個 external consistency 演算法都建立在「時間是一個 interval、不是一個點」這個 API 設計上。

### 硬體基礎：GPS + 原子鐘冗餘

每個 datacenter 部署 GPS 接收器 + 原子鐘（armageddon master、用來防 GPS 全網干擾）、time master 之間互相比對排除離群值、TrueTime daemon 從多個 master 拉時間並算 worst-case bound。GPS 給 absolute time reference、原子鐘給 short-term stability（GPS 短暫失聯時仍能用 drift bound 撐過去）。雙來源是為了把 ε 的失敗模式限制在「絕大多數時間 ε ≤ 7ms、極端事件下 ε spike 但不會無限制漂移」。

### 不確定性 ε（epsilon）

跨 datacenter 同步 + clock drift 估計、ε 目標維持在 1-7ms 區間。

**Fact source 分層警告**：1-7ms 是 Google 2012 OSDI 論文 + Spanner 公開文件（2024-2026）引用的範圍、9.C10 dogfood case 未直接揭露 production ε 分布。引用時這組數字明標「來自 Spanner vendor docs / 2012 論文、不是 9.C10 case 直接揭露」、避免讀者把兩種來源混為一談。

### Commit wait 機制：external consistency 的核心

read-write transaction 要拿 commit timestamp s 時、Spanner 設 `s = TT.now().latest`、然後 *等待* 直到 `TT.after(s)` 才回 ACK。這段「等」就是 [Commit Wait](/backend/knowledge-cards/commit-wait/) — Spanner 特有的物理延遲、由 TrueTime ε 主導、跟 [Cross-Region Quorum](/backend/knowledge-cards/cross-region-quorum/) 的網路 RTT 是兩個獨立的延遲來源、不能混算。

```text
T1 開始 commit            T1 確定可回 ACK
       |                          |
       v                          v
TT.now().earliest .... s = TT.now().latest .... TT.after(s)
       |--------- ε --------|
                            |---------- commit wait ≈ ε ----------|
       |---------- total commit wait ≈ 2ε（從拿 s 那刻開始） ---------|
```

commit wait ≈ 2ε 的數學保證了「下一個 transaction 拿到的 timestamp 一定 > s」、external consistency 的全序性質就由這個 wait 撐住。**Fact source 分層**：commit wait ≈ 2ε 的推導來自 Spanner 2012 OSDI 論文 + 官方文件、不是 9.C10 case 直接展開實作層數學。引用這條數學要附「來源 vendor docs / paper」、避免讀者誤以為這是 case 揭露。

### 跟通用 linearizability 卡片的差異

[Linearizability](/backend/knowledge-cards/linearizability/) 只要求「存在某個全序」、external consistency 進一步要求「全序跟 real-time 順序一致」。TrueTime 是把後者變可實作的關鍵 — 它把跨 datacenter 的「real-time 順序」變成可機械判定的 `TT.after(s)`、不需要全局 coordinator 來決定誰先誰後。對應的概念卡：[external-consistency](/backend/knowledge-cards/external-consistency/)、[linearizability](/backend/knowledge-cards/linearizability/)、[quorum](/backend/knowledge-cards/quorum/)。

## 操作流程：怎麼觀測 ε 跟調用 TrueTime

TrueTime 本身不對外暴露給 application 操作、ε / commit wait 由 Spanner 內部執行。團隊能做的是 *觀測* ε 跟 *選擇* 不同強度的 read consistency。

### 觀測 ε

Cloud Monitoring metric `spanner.googleapis.com/instance/clock_skew_ms` 是 ε 的對外指標、判讀正常 < 7ms、異常 spike > 50ms 代表 time master 失聯或 GPS 干擾。把這條 metric 跟 `commit_latencies` p99 配成 evidence pair：ε spike 時 commit latency heatmap 應該整層平移、若 commit latency 動但 ε 沒動、不是 TrueTime 的問題、是 quorum / network 的問題。

### 跨 region instance 配置時的 TrueTime 影響

voting region 越分散、ε 上限越高、commit wait 越長 → write latency 直接受 ε 影響。multi-region instance config 在做 region layout 決策時要把「voting region 散布範圍」當 latency budget 的固定支出、不是配完才補觀測。

### read-only transaction 的 staleness 選項

```text
strong              → 等 TrueTime 確認可讀最新、付完整 commit wait + quorum cost
exact_staleness(t)  → 讀 t 秒前快照、避開 commit wait、適合 reporting / analytics
bounded_staleness(t)→ 容忍 t 秒、可讀最近的本地 replica 副本、不跨 region quorum
```

stale / bounded staleness 走的是 Spanner 版的 [Follower Read](/backend/knowledge-cards/follower-read/) — 本地 replica serve 不參與 commit 的 read、避開跨 region quorum 把 read latency 降到 single-region 等級。

三者 trade-off 在 SDK 層顯式設定、不是 isolation level：

```go
// Spanner Go SDK 範例（time-sensitive、查最新文件確認 API）
client.Single().
    WithTimestampBound(spanner.MaxStaleness(10 * time.Second)).
    Query(ctx, statement)
```

### 驗證點跟 rollback boundary

跑 cross-region write + cross-region read benchmark、量 p50 / p99 write latency、確認 ≈ 2ε + quorum RTT 的數量級。TrueTime 配置不由用戶調、commit wait 由 Spanner 自動執行；應用層 rollback boundary 在「改用 stale read / bounded staleness」而不是「關掉 TrueTime」 — TrueTime 是 Spanner 內部不可關的機制、不是 feature flag。

## 失敗模式：ε 暴衝跟誤用 strong read

### ε 暴衝（time master 失聯）

GPS 干擾、datacenter time master 雙故障、ε 從 4ms 跳到 200ms → 所有 write 的 commit wait 暴增、p99 write latency 從 50ms 變 500ms。徵兆是 Cloud Monitoring `commit_latencies` heatmap 整層平移、`clock_skew_ms` 同步上升。根因不在 application、在 datacenter 物理層、修法是等 GCP 內部 time master 恢復、應用層只能臨時降到 bounded staleness 救 read path。

### 把 strong read 用在不需要的路徑

報表、analytics、user profile fetch 全用 strong read、每次 read 都付 TrueTime 對齊代價、p99 read 跟 write 同步退化。徵兆是 `commit_latencies` 沒動、但 `api/request_latencies` for `ExecuteSql` 整體上升。修法是把 read path 分類、reporting / analytics 改 bounded staleness、保留 strong read 給「讀後決策再寫」的 critical path。

### 在 client 側做「自己的 timestamp」

application 用 `time.Now()` 當業務 key、跨 region 寫入時 client clock skew 直接破壞順序 — Spanner 內部 external consistency 對、業務層卻錯。徵兆是對帳系統發現 timestamp 順序顛倒、但 Spanner audit log 都 OK。修法是業務層 timestamp 全改用 Spanner `PENDING_COMMIT_TIMESTAMP` sentinel、commit 時由 Spanner 填、不靠 client clock。

### 把 Spanner 當 single-region SQL 用、卻配 multi-region instance

每筆 write 都付跨洲 quorum + commit wait、cost 跟 latency 都浪費。徵兆是 instance config 是 multi-region 但實際 read 99% 來自單一 region、write 也是。修法是降到 regional instance、把跨 region 需求改用 read-only replica 或 export 到 BigQuery。

### ε 沒監控

團隊直到事故才看 clock_skew metric、被動處理而非主動告警。建議 `clock_skew_ms > 20ms` warn、`> 50ms` page、跟 commit_latencies p99 偏離 baseline 2x 一起當 saturation discovery 訊號（回 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)）。

## 容量與觀測：TrueTime ε 是 latency budget 的固定支出

必看 metric：

```text
commit_latencies (p50 / p95 / p99)        → commit wait + quorum RTT 的總和
api/request_count by method               → strong read vs stale read 的分布
instance/cpu/utilization_by_priority      → high / low priority 分流
clock_skew_ms                             → TrueTime ε 的對外指標
```

用 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 框架把 TrueTime ε 跟 commit latency 配成 evidence pair。Capacity 規劃路由回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、把「ε × write rate」當 latency budget 的固定支出 — 寫越多筆、commit wait 累積成本越高、不是 free。

Alert 建議：

| Metric                     | Warn          | Page        |
| -------------------------- | ------------- | ----------- |
| `clock_skew_ms`            | > 20ms        | > 50ms      |
| `commit_latencies` p99     | baseline 1.5x | baseline 2x |
| `low_priority_utilization` | > 80%         | > 90%       |

### Line-rate scaling 驗證（呼應商業邏輯先行段）

擴 node 數時量「read throughput / node」是否維持線性 — 9.C10 揭露的 2 → 4 nodes = 45K → 90K reads/sec 是 Google internal dogfood 的線性模式、不是客戶 SLA 承諾。團隊在自己 instance 上要驗證的不是「能不能達到 90K reads」、是「擴 node 後 throughput / node 有沒有保持線性」。若曲線 sub-linear、檢查是否 hot split / hot range / Paxos group 不均、TrueTime 機制本身不解這層。

## 邊界與整合：何時不用 TrueTime（或不用 Spanner）

### 何時改用 stale read

reporting / analytics / dashboard 場景改用 bounded staleness 換 cost、不付 commit wait 的 latency tax。判準：若這個 read path 用 5 秒前的資料不會影響業務決策、改 stale read；若會、保留 strong read。

### 何時不該升 Spanner

單 region workload 不該為了 external consistency 升 Spanner、Cloud SQL + serializable isolation 已經夠。9.C10 dogfood 揭露的線性 scaling 是「跨 region + 大規模」場景的設計目標、單 region 用戶拿不到對應的 cost / latency benefit。詳見遷移判讀：[Cloud SQL → Spanner Migration Playbook](../migrate-from-cloud-sql-pg/) 的 no-go condition 段。

### Sibling deep articles 路由

- [consistency-models-comparison](../consistency-models-comparison/)：為什麼 external consistency ≠ serializability ≠ linearizability、line-rate scaling 對照表、cross-region quorum 100-200ms 物理硬限
- [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)：schema change 也用 TrueTime 保證 version 邊界、parent-child storage layout
- [migrate-from-cloud-sql-pg](../migrate-from-cloud-sql-pg/)：cutover 階段需要把 application 對 timestamp 的假設審一遍（特別是 client 端 `time.Now()` 那條失敗模式）

### 跟 1.x 章節的互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)：Spanner 是 PC 系統的代表、Cosmos DB AP 系統當對照
- [transaction boundary](/backend/knowledge-cards/transaction-boundary/)：external consistency 是 transaction boundary 的全球延伸

### Anti-recommendation

讀者讀完本文應該能判斷：TrueTime 不是「保證強一致」的功能、是「換 scaling 路徑」的核心；若團隊只想要「強一致」、不需要「跨節點線性擴展」、PostgreSQL serializable + 應用層補上 client-side ordering 就夠、不必為 TrueTime 付 GCP lock-in 的 cost。
