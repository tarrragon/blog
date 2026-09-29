---
title: "Spanner TrueTime API 深度：GPS + 原子鐘、commit wait、為什麼 line-rate scaling 才是設計目的"
date: 2026-05-27
description: "TrueTime 是手段、line-rate scaling 才是 Spanner 的設計目的。本文先扣商業邏輯：傳統 OLTP coordinator 為什麼是 bottleneck、Spanner 怎麼用 TrueTime + Paxos 換成拓樸感知多 leader；再展開 TrueTime ε / commit wait 數學、ε 暴衝失敗模式、cross-region voting 對 latency 的影響、跟 Google 內部 Spanner 規模案例揭露的線性擴展模式對照"
weight: 30
tags: ["backend", "database", "spanner", "global-sql", "truetime", "external-consistency", "deep-article"]
---

本文的範圍是 Spanner 的 TrueTime API：它如何消滅 single coordinator bottleneck、換到 line-rate scaling，TrueTime 的 API 與硬體基礎，觀測 ε 與調用 TrueTime 的方式，ε 暴衝與誤用 strong read 的失敗模式，以及 ε 在 latency budget 裡的固定支出。

---

## 商業邏輯先行：TrueTime 是手段、line-rate scaling 才是目的

TrueTime 的設計目的是消滅 single coordinator bottleneck、讓 OLTP 拿到 line-rate scaling — external consistency 只是這條路徑上拿到的副產品。讀者若把 TrueTime 當成「一個保證 external consistency 的精巧時間 trick」、會誤把工具當目標、後續所有 commit wait / Paxos / GPS 細節都解錯方向。

傳統 OLTP（PostgreSQL、MySQL、Cloud SQL）跨節點交易要靠一個 coordinator 決定全局順序、coordinator 本身就是 bottleneck。`1x node = 1x throughput` 的線性擴展在 single-primary 模型撞牆、想 scale 只能往應用層 sharding 走、付管理 shard key / 跨 shard query / resharding 的代價。Spanner 換掉這條路徑：TrueTime 把 wall-clock 變成跨 datacenter 可比較的 *interval*、Paxos 把 coordinator 變成「拓樸感知的多 leader」（每個 [Range Sharding](/backend/knowledge-cards/range-sharding/) split 自己的 Paxos group 各自前進）、commit timestamp 用 TrueTime 對齊到 real-time 順序、不再需要一個全局 coordinator 串行所有 transaction。

[Cloud Spanner planetary scale 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)（Google Ads、Play、Search 等內部服務跑在 Spanner 上的規模數據）揭露的線性擴展證據：「2 nodes → 45K reads/sec、4 nodes → 90K reads/sec」是 Spanner 設計目標的直接證據、不只是 marketing 數字。這組數字揭露 Spanner external consistency 不是「加強版 serializable isolation」、是「coordinator 換拓樸」的 paradigm shift。寫到這裡讀者該意識到一件事：選 Spanner 不是選一個更貴更強的 SQL、是選一條 *把 coordinator 拆掉* 的 scaling 路徑。

**Dogfood 邊界**：planetary scale 案例是 Google 內部自用（dogfood）的數據、不是 customer-facing capacity 參考。「10 億 req/sec」是 Google 全使用者加總、不是單一 instance 配額；「2 nodes → 45K reads / 4 nodes → 90K reads」是 Google internal benchmark 揭露的線性擴展 *模式*、不是客戶 SLA 承諾。

**來源分層**：「傳統 OLTP 的 coordinator 是 bottleneck、TrueTime + Paxos 把它換成拓樸感知的多 leader」這套推論，是合併 Spanner 2012 OSDI 論文、公開文件（2024-2026）與 planetary scale 案例寫成的。案例本身直接揭露的只有線性擴展數字與 dogfood 邊界，沒有展開實作層細節。

## 問題情境：跨 region OLTP 的順序漏洞

跨 region OLTP 想保證「全球用戶看到的交易順序跟 wall clock 一致」、但 NTP 同步誤差動輒 10-100ms、足夠讓 region A 已 commit 的計費事件被 region B 看到一個更新的 timestamp 卻是舊狀態。讀者徵兆通常從這幾個地方浮現：分散式系統團隊在 Cloud SQL / Aurora 多 region 上做 read replica、發現「跨 region read 順序顛倒」、audit log timestamp 不可靠、reconcile [對帳](/backend/knowledge-cards/data-reconciliation/)對不上、業務以為自己用了 transaction 就有「強一致」、實際只有 single-node 的 serializable isolation。

真實壓力場景：Google Ads 計費需要把每筆扣款事件放進可驗證的 *外部* 順序、不只是 transaction 內部 serializable。讀者若把這套需求帶回自家系統、會發現一條共同訊號 — 「兩個 transaction 都 commit 成功、用戶體感卻違反順序」這種事故、不是 isolation level 的問題、是 *external consistency* 的問題。

Case anchor：[Cloud Spanner planetary scale 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads / Play 訂閱 / Search 計費跟 TrueTime 綁定。這個案例的數字受〈商業邏輯先行〉一節的 dogfood 邊界約束：它們是設計目標的證據，不是客戶可獲得的配額。

## 核心機制：TrueTime 的 API 跟硬體基礎

TrueTime 對外只有兩個 primitive — `TT.now()` 回傳一個 *interval* `[earliest, latest]`、不是單一時刻；`TT.after(t)` / `TT.before(t)` 判斷一個事件是否確定在 t 之後 / 之前。整個 external consistency 演算法都建立在「時間是一個 interval、不是一個點」這個 API 設計上。

### 硬體基礎：GPS + 原子鐘冗餘

每個 datacenter 部署 GPS 接收器 + 原子鐘（armageddon master、用來防 GPS 全網干擾）、time master 之間互相比對排除離群值、TrueTime daemon 從多個 master 拉時間並算 worst-case bound。GPS 給 absolute time reference、原子鐘給 short-term stability（GPS 短暫失聯時仍能用 drift bound 撐過去）。雙來源是為了把 ε 的失敗模式限制在「絕大多數時間 ε ≤ 7ms、極端事件下 ε spike 但不會無限制漂移」。

### 不確定性 ε（epsilon）

ε 是 `TT.now()` 回傳區間的半寬：`latest - earliest = 2ε`，真實時間保證落在這個區間裡。每台機器上的 TrueTime daemon 依它與 time master 的同步誤差、以及本機時鐘在兩次同步之間可能的 drift 估計 ε；論文量到的 ε 在每個同步週期內從約 1ms 爬到約 7ms，平均約 4ms。

1-7ms 這組數字的出處是 Google 2012 OSDI 論文，planetary scale 案例沒有揭露 production 的 ε 分布。

### Commit wait 機制：external consistency 的核心

read-write transaction 要拿 commit timestamp s 時、Spanner 設 `s = TT.now().latest`、然後 *等待* 直到 `TT.after(s)` 才回 ACK。這段「等」就是 [Commit Wait](/backend/knowledge-cards/commit-wait/) — Spanner 特有的物理延遲、由 TrueTime ε 主導、跟 [Cross-Region Quorum](/backend/knowledge-cards/cross-region-quorum/) 的網路 RTT 是兩個獨立的延遲來源、不能混算。

```text
T1 拿 commit timestamp 的那一刻
  TT.now() = [earliest, latest]      # 區間寬 2ε，真實時間落在其中某處
  s = latest                         # s 不早於任何可能的真實時間
                                     # 此刻 earliest = s - 2ε
commit wait
  反覆呼叫 TT.now()，直到 earliest > s   # 即 TT.after(s) 為真
                                     # earliest 要從 s - 2ε 走到 s 之後，時鐘約走過 2ε
T1 回 ACK
```

等完這段，s 一定已經是過去的時間：任何在 T1 回 ACK 之後才開始的 transaction，拿到的 timestamp 一定大於 s，external consistency 的全序性質就由這段等待撐住。commit wait ≈ 2ε 的推導出處是 Spanner 2012 OSDI 論文的 Commit Wait 一節與官方文件。

### 跟通用 linearizability 卡片的差異

[Linearizability](/backend/knowledge-cards/linearizability/) 要求單一物件上的每個操作看起來在它的呼叫與回應之間的某一刻瞬間生效，所以兩個不重疊的操作之間的先後必須跟 real-time 一致；它的單位是單一操作。external consistency 把同一條 real-time 要求套到跨多列、多個 split 的 transaction 上（文獻裡叫 strict serializability）。TrueTime 是把 transaction 層級的 real-time 順序變可實作的關鍵 — 它把跨 datacenter 的「real-time 順序」變成可機械判定的 `TT.after(s)`、不需要全局 coordinator 來決定誰先誰後。對應的概念卡：[external-consistency](/backend/knowledge-cards/external-consistency/)、[linearizability](/backend/knowledge-cards/linearizability/)、[quorum](/backend/knowledge-cards/quorum/)。

## 操作流程：怎麼觀測 ε 跟調用 TrueTime

TrueTime 本身不對外暴露給 application 操作、ε / commit wait 由 Spanner 內部執行。團隊能做的是 *觀測* ε 跟 *選擇* 不同強度的 read consistency。

### 觀測 ε

截至 2026-09 的 Cloud Monitoring Spanner metric 清單沒有任何揭露 ε 的指標：清單裡沒有 `clock_skew_ms`，也沒有名為 `commit_latencies` 的 metric。團隊觀測得到的是 ε 的下游症狀：`spanner.googleapis.com/api/request_latencies` 用 `method` label 篩出 `Commit`，看 commit 延遲的分布。Spanner 2012 OSDI 論文記載 time master 失聯會讓整個 datacenter 的 ε 一起升高，那時所有 write 的 commit 延遲 heatmap 會整層平移；若只有特定 database 或特定時段的 commit 延遲上升，成因多半在 quorum、網路或熱點。

### 跨 region instance 配置時的 TrueTime 影響

voting region 越分散、跨 region Paxos quorum 的往返時間越長 → write latency 直接受 quorum RTT 影響。ε 由每台機器的本機時鐘 drift、time master 本身的不確定性、以及機器到 time master 的通訊延遲決定，voting region 的散布範圍不在其中；commit wait 通常與 Paxos 通訊重疊進行，跨洲配置下拉高 write latency 的是 quorum RTT。multi-region instance config 在做 region layout 決策時要把「voting region 散布範圍」當 latency budget 的固定支出、不是配完才補觀測。

### read-only transaction 的 staleness 選項

```text
strong              → 讀當下最新已提交資料、serving replica 通常先向 leader 發 RPC 確認要套用到哪個 timestamp、不付 commit wait
exact_staleness(t)  → 讀 t 秒前快照、replica 可能省掉向 leader 確認的 RPC、適合 reporting / analytics
bounded_staleness(t)→ 容忍 t 秒、可讀最近的本地 replica 副本、不跨 region quorum
```

stale / bounded staleness 走的是 Spanner 版的 [Follower Read](/backend/knowledge-cards/follower-read/) — 本地 replica serve 不參與 commit 的 read、避開跨 region quorum 把 read latency 降到 single-region 等級。

strong、exact staleness、bounded staleness 的選擇在 SDK 層顯式設定、不是 isolation level：

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

GPS 干擾、datacenter time master 雙故障、ε 從 4ms 跳到 200ms → 所有 write 的 commit wait 暴增、p99 write latency 從 50ms 變 500ms。徵兆是 Spanner `api/request_latencies`（`method` 為 `Commit`）的 heatmap 整層平移；截至 2026-09 的 Cloud Monitoring metric 清單沒有揭露 ε 的指標，團隊只看得到 commit 延遲，看不到 ε 的數值。根因不在 application、在 datacenter 物理層、修法是等 GCP 內部 time master 恢復、應用層只能臨時降到 bounded staleness 救 read path。

### 把 strong read 用在不需要的路徑

報表、analytics、user profile fetch 全用 strong read、serving replica 每次 read 都可能多一次向 leader 確認最新 timestamp 的 RPC、p99 read 跟 write 同步退化。徵兆是 `api/request_latencies` for `Commit` 沒動、但 `api/request_latencies` for `ExecuteSql` 整體上升。修法是把 read path 分類、reporting / analytics 改 bounded staleness、保留 strong read 給「讀後決策再寫」的 critical path。

### 在 client 側做「自己的 timestamp」

application 用 `time.Now()` 當業務 key、跨 region 寫入時 client clock skew 直接破壞順序 — Spanner 內部 external consistency 對、業務層卻錯。徵兆是對帳系統發現 timestamp 順序顛倒、但 Spanner audit log 都 OK。修法是業務層 timestamp 全改用 Spanner `PENDING_COMMIT_TIMESTAMP` sentinel、commit 時由 Spanner 填、不靠 client clock。

### 把 Spanner 當 single-region SQL 用、卻配 multi-region instance

每筆 write 都付跨洲 quorum + commit wait、cost 跟 latency 都浪費。徵兆是 instance config 是 multi-region 但實際 read 99% 來自單一 region、write 也是。修法是降到 regional instance、把跨 region 需求改用 read-only replica 或 export 到 BigQuery。

### commit 延遲沒監控

團隊直到事故才看 commit 延遲、被動處理而非主動告警。ε 沒有對外 metric（截至 2026-09 的 Cloud Monitoring metric 清單），告警要設在 commit 延遲上：建議 `api/request_latencies`（`method` 為 `Commit`）p99 偏離 baseline 1.5x warn、2x page，當 saturation discovery 訊號（回 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)）。

## 容量與觀測：TrueTime ε 是 latency budget 的固定支出

必看 metric：

```text
api/request_latencies by method=Commit    → commit 延遲（commit wait 與 quorum RTT 重疊後的結果）
api/request_count by method               → strong read vs stale read 的分布
instance/cpu/utilization_by_priority      → high / low priority 分流
```

用 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 框架把 commit 延遲跟 strong read / stale read 的 request 分布配成 evidence pair。Capacity 規劃路由回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、把「ε × write rate」當 latency budget 的固定支出 — 寫越多筆、commit wait 累積成本越高、不是 free。

Alert 建議：

| Metric                                 | Warn          | Page        |
| -------------------------------------- | ------------- | ----------- |
| `api/request_latencies`（`Commit`）p99 | baseline 1.5x | baseline 2x |
| `low_priority_utilization`             | > 80%         | > 90%       |

### 擴 node 之後 throughput / node 要維持線性

擴 node 數時量「read throughput / node」是否維持線性 — planetary scale 案例揭露的 2 → 4 nodes = 45K → 90K reads/sec 是 Google 內部自用的線性模式、不是客戶 SLA 承諾。團隊在自己 instance 上要驗證的不是「能不能達到 90K reads」、是「擴 node 後 throughput / node 有沒有保持線性」。若曲線 sub-linear、檢查是否 hot split / hot range / Paxos group 不均、TrueTime 機制本身不解這層。

## 邊界與整合：何時不用 TrueTime（或不用 Spanner）

### 何時改用 stale read

reporting / analytics / dashboard 場景改用 bounded staleness 換 cost、省下 strong read 向 leader 確認最新 timestamp 的那次 RPC。判斷標準：若這個 read path 用 5 秒前的資料不會影響業務決策、改 stale read；若會、保留 strong read。

### 何時不該升 Spanner

單 region workload 不該為了 external consistency 升 Spanner、Cloud SQL + serializable isolation 已經夠。planetary scale 案例揭露的線性 scaling 是「跨 region + 大規模」場景的設計目標、單 region 用戶拿不到對應的 cost / latency benefit。詳見遷移判讀：[Cloud SQL → Spanner Migration Playbook](../migrate-from-cloud-sql-pg/) 的 no-go condition 段。

### 相關的 Spanner 文章

- [Spanner Consistency Models 對照](../consistency-models-comparison/)：為什麼 external consistency ≠ serializability ≠ linearizability、line-rate scaling 對照表、cross-region quorum 100-200ms 物理硬限
- [Spanner Schema Migration Without Downtime + Interleaved Tables](../schema-migration-interleaved-tables/)：schema change 也用 TrueTime 保證 version 邊界、parent-child storage layout
- [Migration Playbook：Cloud SQL for PostgreSQL → Cloud Spanner](../migrate-from-cloud-sql-pg/)：cutover 階段需要把 application 對 timestamp 的假設審一遍（特別是 client 端 `time.Now()` 那條失敗模式）

### 跟資料庫模組主章節的互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)：Spanner 是 PC 系統的代表、Cosmos DB AP 系統當對照
- [transaction boundary](/backend/knowledge-cards/transaction-boundary/)：external consistency 是 transaction boundary 的全球延伸

### Anti-recommendation

讀者讀完本文應該能判斷：TrueTime 不是「保證強一致」的功能、是「換 scaling 路徑」的核心；若團隊只想要「強一致」、不需要「跨節點線性擴展」、PostgreSQL serializable + 應用層補上 client-side ordering 就夠、不必為 TrueTime 付 GCP lock-in 的 cost。
