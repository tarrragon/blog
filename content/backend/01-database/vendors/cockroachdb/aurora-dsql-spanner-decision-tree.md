---
title: "CockroachDB vs Aurora DSQL vs Spanner：撞牆訊號分型 + 選型決策樹"
date: 2026-05-27
description: "Distributed SQL 三選一決策樹。先用撞牆訊號分型識別 driver path（DoorDash 單主寫入撞牆 / Netflix Cassandra 缺口 / Hard Rock 合規驅動）、再走跨雲、雲商生態、風險預算、PG 相容、管理負擔、team size、vendor sizing barrier 各題。含 PostgreSQL 相容性 audit checklist、Spanner 100 pu sizing barrier、Hard Rock 「省 10-20 工程師」機會成本警示、Netflix Database Platform Team 規模"
weight: 100
tags: ["backend", "database", "cockroachdb", "aurora-dsql", "spanner", "distributed-sql", "decision-tree", "deep-article"]
---

> 本文整理 distributed SQL 的選型：先用撞牆訊號分型識別自己屬於哪條 driver path、再做三家 vendor 對比、最後檢查 team size 與 vendor 的 sizing 邊界。上游的全球分散式 OLTP 取捨見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)。

---

## 先識別 driver path、再比 vendor

團隊評估「全球分散式 OLTP 三選一」時最常見的源頭錯誤：先比 vendor、再回頭問「我為什麼要 distributed SQL」。三家 vendor 文件都說「跨 region 強一致 SQL」、看不出實際取捨；做錯選擇後遷移成本極高。

正確順序應該反過來：先識別 *自己為什麼要評估 distributed SQL*、再進 vendor 比較。三條 driver path 各自的訊號、適配 vendor、決策路徑都不同 — 不識別 driver path 直接比 vendor 是源頭錯誤。

讀者進來最常問的問題（多數會問錯順序）：

- 我是不是真該換 distributed SQL、還是 Aurora / Cloud SQL 還能撐？
- Spanner 在 Google 跑了 10 年、CockroachDB 跟 DSQL 比較新、成熟度差多少？
- 我有 PostgreSQL 應用、三家相容性差在哪？
- 跨雲是硬需求還是被 fear 推的？
- DSQL 2025-05 才 GA、production 風險多大？
- 我團隊 50 人能不能養 self-managed CockroachDB？
- Spanner 100 pu 起跳對我中小 PG workload 划算嗎？

這些問題本文都會回答，但要先回答「為什麼要評估 distributed SQL」——也就是自己屬於哪條 driver path。

### 三條 driver path 的 case anchor

- [DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)：Aurora Postgres 1.636 M QPS single-primary 撞牆 → 換 multi-primary、PostgreSQL wire 相容降低遷移阻力
- [Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)：Cassandra eventual consistency 撐不住 transactional → 補 distributed SQL、self-managed 380+ cluster + Database Platform Team
- [Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)：Wire Act 合規驅動 + 50 人 tech team + Outposts 混合部署

對照 [Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 提供 Spanner ground truth（含 sizing barrier）、[Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 提供 Aurora 受監管金融的另一條路徑、[DraftKings Aurora financial ledger](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 提供 Aurora 內 business sharding 路徑（不換引擎）。

## 撞牆訊號分型：識別自己的 driver path

讀者進來前先回答：你 *為什麼* 要評估 distributed SQL？三條 driver path 各自的訊號、適配 vendor、決策路徑都不同。

### single-primary 寫入撞牆（DoorDash 路徑）

訊號：

- 寫入量持續成長、Aurora / RDS / Cloud SQL primary CPU + WAL flush rate 接近上限
- 轉折點 *不是 IOPS、是 primary CPU + WAL flush rate*（DoorDash case 的〈策略〉段）
- 已嘗試 vertical scale primary、撞 instance ceiling

DoorDash concrete reference：2020-04-17 高峰 > 1.636 M QPS、multi-hour outage（觀察段表格）。**Scope warning（case 自帶警示）**：1.636 M QPS 是 *Aurora 撞牆的痛點* — 不是「CockroachDB throughput claim」、case 沒揭露遷移後單一 CockroachDB cluster 的峰值、只說「跑更多 cluster、alert volume 反而下降」。

適配 vendor：CockroachDB / Aurora DSQL / Spanner 都解、選擇看其他軸。

### eventual consistency 缺口（Netflix 路徑）

訊號：原本用 Cassandra / Riak / DynamoDB eventual consistency、遇到 *5 條件並存* 需求：

1. multi-active topology（多 region 都可寫）
2. global consistent secondary index（跨 region 一致的二級索引）
3. global transaction（跨 row / 跨 region 的 ACID）
4. open source
5. SQL

Cassandra 在 transactional 場景下 *湊不齊* 這五項。Netflix 2019 評估後選 CockroachDB（case 的〈判讀〉段列出這五項條件）。具體場景：Studio Cloud Drive（強一致 metadata + 全球可寫）、Open Connect 控制平面、Spinnaker（持續交付）、Maestro（ML / 資料 workflow）、Gaming 控制平面。

適配 vendor：CockroachDB（open source + SQL 兩條件硬卡）、Spanner（若 GCP-only 可放鬆 open source 要求）。

### 合規驅動的地理邊界 + 跨 boundary 業務邏輯需求（Hard Rock 路徑）

訊號：

- 法規要求資料留某地理邊界（Wire Act 跨州、GDPR 跨國、各州博彩牌照）
- *同時* 業務邏輯需要跨 boundary（跨州統一帳戶 / 跨州 reporting / 欺詐偵測）

Hard Rock concrete reference：跨 8 州（AZ / IN / TN / FL / OH / IL / NJ / VA）+ AWS Outposts + 邏輯一個 cluster（觀察段表格）。詳細 schema 配置見 [locality-aware schema](../locality-aware-schema/)。

適配 vendor：CockroachDB（locality + placement + Outposts）、Spanner（GCP region 內 placement、無 Outposts 等效）、Aurora DSQL 跨 region 強一致但 Outpost 部署現階段未完整覆蓋。

### 不該換 distributed SQL 的訊號

- single-region OLTP 已足夠
- 寫入量未撞 single-primary 天花板（Aurora db.r6g.16xlarge 還沒滿）
- 無跨 region 業務需求
- 無跨 boundary 合規需求

→ PostgreSQL / Aurora 足夠、distributed SQL overhead（寫入 2-5x latency、ops 複雜度）不划算。對應 [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 走 Aurora + application sharding 的路徑、不換引擎也能解單主寫入瓶頸。

> **數字口徑**：本段「2-5x latency」屬通用工程估算（Raft / Paxos round trip 跟 single-leader replication 的 latency ratio）、case 未直接揭露對照數字、實際值依拓樸 / 寫入大小 / 一致性層次而異、應該以自家 benchmark 驗證。

## 核心機制：三軸 vendor 對比

完成 driver path 識別後、進三軸 vendor 對比。

### 部署 topology

| Vendor      | 部署                                    | 何時是硬條件                 |
| ----------- | --------------------------------------- | ---------------------------- |
| CockroachDB | cross-cloud + on-prem + Cockroach Cloud | 跨雲 / on-prem hybrid 必要時 |
| Spanner     | GCP-only                                | 不適合非 GCP 環境            |
| Aurora DSQL | AWS-only                                | 不適合非 AWS 環境            |

合規驅動 path 的場景（Hard Rock Outposts hybrid）強制走 CockroachDB — Spanner 與 Aurora DSQL 不提供等效部署。

### Managed 成熟度

**Scope warning（來源分層）**：3 case 都沒揭露成熟度比對、本軸依 case + vendor 公開文件 + 外部知識合成：

- **Spanner**：10+ 年 Google 內部 + 外部 GA（依 Cloud Spanner case + Google research paper、屬 vendor 公開文件 + dogfood frame）
- **CockroachDB**：自管 + Cockroach Cloud（managed 較新、依 Cockroach Labs 公告）
- **Aurora DSQL**：2024-12 re:Invent 發表 preview、2025-05-27 GA（依 AWS 公告）

「Spanner 10+ 年」是 vendor 公開資訊與 Google 內部使用經驗的合成、不是 case 揭露的 production stability 數字；Aurora DSQL 的 GA 時間取自 AWS 公告，production case 還在累積。

### SQL 相容性

| Vendor      | SQL                                     | 相容程度                                |
| ----------- | --------------------------------------- | --------------------------------------- |
| CockroachDB | PostgreSQL wire protocol                | *protocol-level* 相容、SQL 行為要 audit |
| Spanner     | GoogleSQL + 部分 PostgreSQL 方言        | GoogleSQL native、PG 方言是子集         |
| Aurora DSQL | PostgreSQL（AWS managed control plane） | PostgreSQL-compatible、AWS 操作模型     |

### PostgreSQL 相容性 audit checklist（DoorDash 揭露的警語展開）

DoorDash case 揭露 PG wire *protocol-level* 相容、SQL 行為「仍要驗證」。把這個警語展開成 audit checklist：

1. **Serializable default**：CockroachDB default SERIALIZABLE、PG default READ COMMITTED → application transaction 行為差異（細節見 [transaction retry pattern](../transaction-retry-pattern/)）。Aurora DSQL 預設行為要看 AWS 公告。
2. **Retry semantics**：CockroachDB 發 `40001 serialization_failure`、application 必須包 retry loop。PG / Aurora 預設不需要、application 沒 retry middleware。Aurora DSQL 比照 CockroachDB 模型、需要 retry loop。
3. **Partial index**：CockroachDB 支援程度與 PG 有差異、application 用到的 partial index 要逐一驗證。Spanner GoogleSQL 跟 PG 行為不同。
4. **其他 SQL 行為**：sequence、auto-increment、stored procedure、custom function、extension 等都需 case-by-case audit。

DoorDash case 揭露的是「PG wire protocol-level 相容、SQL 行為要 audit」這個 fact；上面 checklist 的內容是通用工程整理，不是 DoorDash case 直接揭露。

### Consensus 機制差

| Vendor      | 共識                                                                          | 硬體依賴                       |
| ----------- | ----------------------------------------------------------------------------- | ------------------------------ |
| CockroachDB | [Hybrid Logical Clock](/backend/knowledge-cards/hybrid-logical-clock/) + Raft | 純軟體 + NTP                   |
| Spanner     | TrueTime + Paxos                                                              | GPS + atomic clock             |
| Aurora DSQL | 類 Spanner 概念、AWS 專屬                                                     | AWS timing infra（未完全公開） |

三家共識機制的差異直接決定 [external consistency](/backend/knowledge-cards/external-consistency/) 的實作路徑：Spanner 用 TrueTime + commit-wait 撐 external consistency；CockroachDB 用 HLC + max-offset 撐 serializability 與 single-key linearizability、不保證 external consistency（strict serializability）；Aurora DSQL 走類 Spanner 路徑但細節未完全公開。三家 multi-region 配置都吃 [Cross-Region Quorum](/backend/knowledge-cards/cross-region-quorum/) 的物理 latency tax。詳細機制見 [HLC + Raft consensus](../hlc-raft-consensus/)。

### Pricing model 差

- **CockroachDB self-managed**：node × resource、cluster 至少 3 node
- **Cockroach Cloud / Spanner / DSQL**：consumption-based（read / write / storage / network）

### Sizing barrier 邊界（Spanner case 揭露）

Spanner 100 processing unit 起跳是 *最小 footprint* — 對中小 PostgreSQL workload 是 cost 邊界：

- workload 月寫入若只夠 PG db.m6g.large 級別、付 Spanner 100 pu 起跳 cost 不對
- CockroachDB 最小 3 node、storage / compute 線性 — 中小 workload 較友善
- Aurora DSQL consumption-based 無 minimum、中小 workload 最友善（但 production case 累積較少）

判讀：sizing barrier 是 *vendor 強制最小 footprint*、不是「啟動成本」— 即使 workload 縮小、minimum 不會降。中小 PG workload 直接套 Spanner = 付不必要的 minimum cost。

對應 [distributed SQL 卡](/backend/knowledge-cards/distributed-sql/)、[quorum 卡](/backend/knowledge-cards/quorum/)、[vendor lock-in 卡](/backend/knowledge-cards/vendor-lock-in/)。

## 決策樹：從跨雲需求到 vendor sizing

撞牆訊號分型已經確定 driver path（single-primary 寫入撞牆、eventual consistency 缺口、合規驅動）。以下依序問跨雲、雲商生態、風險預算、PG 相容、管理負擔、team size、vendor sizing，在三家 vendor 裡篩出選擇。

### 是否硬需求跨雲 / on-prem？

- **Yes** → CockroachDB（唯一選項；對應 Netflix 跨 AWS region、Hard Rock AWS Outposts 混合）
- **No** → 看〈已在 AWS 還是 GCP 還是中立？〉

跨雲是 *硬需求* 而不是 *fear-driven* 訊號：

- 真硬需求：法規明文跨雲、acquisition 後多雲整合、vendor risk 政策強制
- fear-driven：「萬一 AWS 全球 outage」（多數公司實際走 single-cloud、跨雲 portability premium 卻沒實際 multi-cloud 部署）

> **數字口徑**：本段「多數公司 single-cloud」屬通用工程估算、case 未揭露明確比例、實際分佈依產業 / 監管 / 規模而異。判斷自己是否需要跨雲時、看具體規範跟 risk 條款、不直接套通用比例。

### 已在 AWS 還是 GCP 還是中立？

- **AWS 深** → Aurora DSQL（操作模型對齊、PostgreSQL 相容）
- **GCP 深** → Spanner（10 年成熟、Google 內部驗證）
- **中立 / 多雲** → CockroachDB（可 portable）

雲商生態深度判讀：IAM / VPC / monitoring / cost mgmt 已深度整合 AWS → Aurora DSQL 整合阻力低；同樣道理 GCP → Spanner。

### production 風險預算有多少？

- **低**（金融 / 醫療）→ Spanner（最成熟）或 CockroachDB（>5 年外部 production case）
- **中** → 三者皆可
- **高**（願意當 early adopter）→ Aurora DSQL（2025-05 GA）

風險預算對應的不是「會不會掛」、是「邊界 case 文件成熟度 + production troubleshooting case 量」。Aurora DSQL 2025-05 GA、production case 累積中、邊界 case 仍在被發現。

### PostgreSQL 相容性是不是 hard requirement？

- **Yes**（既有 application）→ CockroachDB 或 Aurora DSQL（兩者都做 PG 相容、但走 audit checklist 驗證 SQL 行為）
- **No** → Spanner（GoogleSQL 也可）

PG hard requirement 訊號：application 用 PostgreSQL-specific feature（partial index、JSONB operator、PostGIS、PG extension 生態）、ORM / driver 深度綁 PostgreSQL wire。

### 管理負擔誰承擔？

- **自管** → CockroachDB（唯一可自管）
- **Managed** → 都行、依雲商生態

自管 vs managed 不只是「省人月」、是「邊界 case 出現時誰修」— managed 的 vendor 負責、自管的自己負責。

### team size 夠不夠自管（Hard Rock + Netflix 揭露）

distributed SQL 的 ops 槓桿來自系統內建 Raft / placement 把「DBA 養單區、跨區 sync 養運維」工作量壓進系統內。

Hard Rock 50 人 tech team 估「若用 PostgreSQL 需多加 10-20 工程師」（case 的〈觀察〉表格與〈策略〉段）。**Case 自帶警示**：「省了 10-20 工程師」是 *機會成本*（沒招那麼多 DBA）、*不是* 節省支出（已 hire 後解雇）。distributed SQL 對小團隊的 ops 槓桿是不必招那麼多 DBA，不是上 CockroachDB 就能裁員或省下既有的人月支出。

Self-managed 規模化的另一極：Netflix 養 380+ cluster 需要 *專屬 Database Platform Team*（含 backup / upgrade / incident response / capacity review）。沒這量級團隊直接 self-host 大規模 cluster，運維負擔會超出團隊能承擔的量，Cockroach Cloud 才是合理路徑。「self-managed cluster 數量 vs 平台團隊規模」的轉折點 case 沒有給出具體閾值，方向是：

- team size 小（< 100 人 tech team、無專屬 DB platform team）→ Cockroach Cloud / Spanner / DSQL（managed）優先
- team size 大 + 有專屬 DB platform team → self-managed CockroachDB 可考慮
- team size 中等但要 self-host 大規模 cluster → 評估專屬 platform team 投資後再決定

### sizing 達不達得到 vendor minimum？

- Spanner 100 processing unit 起跳對中小 PG workload 是成本門檻、月寫入 < 某 baseline 時付 Spanner 起跳費不划算
- 中小 workload 但需 multi-region 強一致 → CockroachDB 3 node 起 / Aurora DSQL consumption-based 較友善
- 大 workload（已過 single-primary 撞牆訊號）→ 三家皆可、回到跨雲、雲商生態、風險預算、PG 相容、管理負擔、team size 各題再篩

## Cluster boundary 顆粒：per-app cluster vs 邏輯一個 cluster

> 本段談的是 *已選 CockroachDB 之後* 的拓樸決策。其他 vendor 的 cluster boundary：Aurora fleet 治理（business sharding / 200 cluster 模式）見 [aurora/read-replica-scaling](../../aurora/read-replica-scaling/)、MongoDB 按 blast radius 切多 cluster（Toyota 20 DB 模式）見 [mongodb/shard-key-selection](../../mongodb/shard-key-selection/)。

選完 vendor 還有一個正交的拓樸決策：CockroachDB cluster 的「顆粒」要切多細。一個微服務一個 cluster（per-app）、還是多個微服務共用一個邏輯 cluster（shared / 邏輯一個 cluster）。這條軸的判讀獨立於跨雲 / 風險預算 / 管理負擔等 vendor 選擇問題、是 *cluster 拓樸* 議題。判讀核心是 [blast radius](/backend/knowledge-cards/blast-radius/) 的取捨 — 是把故障半徑限縮在單服務（per-app）、還是接受邏輯 cluster 內事故跨業務影響但換 transactional cross-domain 能力（邏輯一個 cluster）。

### Per-app cluster（Netflix 380+ 路徑）

每個微服務 / 每個業務邊界各自獨立 cluster。Netflix 揭露的具體形貌：380+ cluster、每個 cluster 規模小（屬「artery of small DBs」哲學、不是巨型 DB）、每個服務 own 自己的 schema 跟容量。

判讀訊號：

- 服務之間資料 *硬隔離*（compliance / blast radius / 不同 SLA tier）— 共用 cluster 一旦 schema migration / hot range 出事、影響面跨服務
- 跨服務 query 需求低（沒有 cross-domain JOIN 場景）
- 容量規劃可以 per-cluster（每個服務自己估、不需共池）
- 有專屬 Database Platform Team 養 cluster lifecycle（backup / upgrade / incident response / capacity review）— ops surface area 隨 cluster 數 *線性成長*

代價：ops surface area 大、每個 cluster 都要獨立 upgrade / monitoring / capacity review。沒這量級的平台團隊直接 self-host 380 個 cluster，運維負擔會超出團隊能承擔的量。

### 邏輯一個 cluster（Hard Rock 路徑）

業務邏輯上是 *一個* CockroachDB cluster、物理上跨多地理 placement（locality + replication zone 把 range 釘到特定 region / AZ / Outpost）。Hard Rock 揭露的具體形貌：跨 8 州 + AWS Outposts、邏輯一個 cluster、跨州統一帳戶 / 跨州 reporting / 欺詐偵測在同一 cluster 內做 transactional query。

判讀訊號：

- 跨服務 / 跨地理需要 *transactional* query（跨州統一帳戶、跨業務統合 reporting）— 拆獨立 cluster 會破壞業務邏輯
- 合規顆粒 *細* 到 region / 州 / AZ、但 *不要求* 完全隔離 cluster（Wire Act 要求州內運算、但允許跨州 application 邏輯）
- Team size 中小（Hard Rock 50 人 tech team）、ops surface area 集中比攤平好管
- 容量規劃集中、跨服務資源共享（不同服務的 range 可以 colocate 同 cluster）

代價：cluster 內複雜度高（要設計 placement / locality / replication zone 把 range 釘對地方）、blast radius 是 *整個邏輯 cluster*、cluster 級事故影響跨業務。

### 兩條路徑的判讀軸

| 判讀軸            | Per-app cluster（Netflix）            | 邏輯一個 cluster（Hard Rock）           |
| ----------------- | ------------------------------------- | --------------------------------------- |
| 服務隔離度        | 硬隔離（不同 SLA / compliance tier）  | 弱隔離（同業務域、共用 placement 策略） |
| 跨服務 query 需求 | 低                                    | 高（transactional cross-domain）        |
| Blast radius      | 限縮在單服務                          | 整個邏輯 cluster                        |
| Ops surface area  | 線性成長（每 cluster 獨立 lifecycle） | 集中但複雜度高（cluster 內 placement）  |
| 容量規劃顆粒      | Per-cluster 獨立估                    | 集中估、跨服務共池                      |
| 平台團隊要求      | 高（cluster 數越多越剛性）            | 中（cluster 數少但 placement 複雜度高） |

判讀順序：先問「跨服務 query 需要 transactional 嗎」— Yes 偏邏輯一個 cluster、No 進下一條；再問「服務之間 SLA / compliance 是否硬隔離」— Yes 偏 per-app、No 看 team / ops 槓桿。

### 跟 Aurora fleet 治理的本質差異

Aurora 的 [fleet 治理](../../aurora/read-replica-scaling/)（read-replica-scaling 的邊界段）展開的是 *Aurora cluster 之間* 怎麼拆（business sharding / blast radius / read fanout），cluster 是 single-primary 抽象、拆 cluster 是 *繞過* single-primary 上限。

CockroachDB cluster boundary 的問題不一樣 — CockroachDB 本身就是 distributed、單 cluster 內可橫向擴展、cluster boundary 是 *業務 / 合規 / blast radius 邊界*、不是繞 single-primary。

| 軸               | Aurora fleet                                | CockroachDB cluster boundary                    |
| ---------------- | ------------------------------------------- | ----------------------------------------------- |
| 拆 cluster 動機  | 繞過 single-primary 寫入上限                | 隔離 blast radius / 合規邊界 / 平台分權         |
| 單 cluster 上限  | 寫入 capacity（single-primary）             | 範圍大（distributed、Raft 內擴）                |
| 跨 cluster query | 應用層拼（無 transactional 保證）           | 一樣應用層拼（除非邏輯一個 cluster）            |
| 典型形貌         | DraftKings 200 cluster（business sharding） | Netflix 380+（per-app）/ Hard Rock 1（logical） |

兩條路徑的 *拆與不拆* 動機本質不同。Aurora 拆是 *被迫*（單 cluster 撐不住）、CockroachDB 拆是 *選擇*（單 cluster 撐得住、拆是為了治理）。

### 跨 vendor 路徑對照

- **Aurora fleet**（DraftKings 200 cluster）— business sharding 繞 single-primary 上限、每 cluster 仍可多 service、平均負載低（[case](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 揭露單 cluster ~80 ops/sec、200 cluster 加總 17K ops/sec）
- **CockroachDB per-app**（Netflix 380+）— 微服務級拆 cluster、artery of small DBs、需要專屬 Database Platform Team；單 cluster 內 [Range Sharding](/backend/knowledge-cards/range-sharding/) + [Leaseholder](/backend/knowledge-cards/leaseholder/) 負責內部 scaling
- **CockroachDB 邏輯一個**（Hard Rock）— 跨地理單一 cluster、locality + placement 撐合規 + transactional 跨域、本地化讀靠 [Follower Read](/backend/knowledge-cards/follower-read/) 降低跨 region cost
- **Aurora fleet per-jurisdiction**（Standard Chartered）— 每監管市場一個 Aurora cluster、合規 *禁止* 跨市場資料流動時的 forced pattern、跟 Hard Rock 對照（合規顆粒粗到要拆 vs 細到能用 placement）

進階閱讀：合規驅動的 cluster boundary 選擇見 [locality-aware-schema](../locality-aware-schema/)；單 cluster 容量規劃見 [hlc-raft-consensus](../hlc-raft-consensus/) 容量與觀測段。

## 失敗模式：常見錯配

### 過度 fear AWS / GCP lock-in

承接〈是否硬需求跨雲 / on-prem？〉的 fear-driven 訊號（多數場景單雲、跨雲是想像中需求）— 把 fear 當硬需求選 CockroachDB，付 portability premium（自管 ops + Cockroach Cloud 較新）卻沒實際 multi-cloud 部署，結果付的是 lock-in 保險、實際沒用上。

判讀：跨雲訊號要 *具體場景*（acquisition 後整合 / 法規明文 / vendor risk 政策強制）、不是 fear。

### 低估 DSQL 成熟度風險

2024-05 GA、production case 少、邊界 case 文件不全 — early adopter 才適合。production 風險預算低的場景（金融 / 醫療 / 合規嚴格）不應該選最新 GA 的服務。

### Spanner 假設 PostgreSQL 全相容

Spanner PostgreSQL interface 是 *子集*、部分 PostgreSQL feature 不支援。應用 migration 仍需 audit、不可直接 lift-and-shift。

### Self-managed CockroachDB 低估 ops cost（Netflix）

Raft / backup / upgrade / monitoring 自管比 PostgreSQL 複雜、DBA bandwidth 沒到位變 disaster。Netflix 養 380+ cluster 需要 *專屬 Database Platform Team* — 含 backup、upgrade、incident response、capacity review。

判讀訊號：「self-managed cluster 數量 vs 平台團隊規模」的轉折點 case 沒有給出具體閾值，方向是 — 小規模 self-managed 不需要、大規模一定需要、之間有 grey zone 要實際評估團隊能力。

### 用 distributed SQL 解 single-region OLTP

90% 場景 PostgreSQL / Aurora 夠用、distributed SQL overhead 是 2-5x latency（Raft round trip 額外成本）。沒撞 single-primary 寫入上限的情況下、上 distributed SQL 是付不必要的 latency premium。

### 合規邊界誤判

受監管市場可能 *不能* 用任何跨境 distributed SQL（Standard Chartered 模式）、要拆每市場獨立 cluster。反過來、合規顆粒小（跨州 vs 跨國）+ 跨 boundary 業務邏輯需求高（跨州統一帳戶）時、Standard Chartered fleet 拓樸不適合、需走 Hard Rock locality + placement 路徑（細節見 [locality-aware schema](../locality-aware-schema/)）。

### Sizing barrier 誤判

中小 PG workload 直接套 Spanner 100 pu 起跳、付的是不必要的 minimum cost。中小規模的硬一致 multi-region workload、CockroachDB 3 node / Aurora DSQL consumption-based 更划算。

### Team size 誤判

把「省 10-20 工程師」當已 hire 後可裁員的節省支出、實際是 *機會成本*（沒招那麼多 DBA）。上 CockroachDB 不代表可裁掉現有 DBA — 現有 DBA 反而要轉型成 distributed SQL 運維。

## 容量與觀測

### 三家共同 metric

- write QPS
- cross-region latency p99
- storage growth
- replica lag（CockroachDB Raft / Spanner Paxos / DSQL replica）

### 觀測黑箱程度

- **CockroachDB Console**：暴露 Raft / range / leaseholder 細節、observability 細
- **Spanner / DSQL**：managed、metric 經 GCP Cloud Monitoring / AWS CloudWatch、observability 黑箱程度高 — 邊界 case troubleshooting 仰賴 vendor support

### 容量公式

write QPS × replication factor × cross-region latency = required node / capacity。中小 workload 撞 vendor minimum 才是真實 cost 下界。

### Cost signal

三家定價模式不同、cross-region traffic 對 cost 影響都大：

- CockroachDB self-managed：node × resource、可控但要自運維
- Spanner：100 pu minimum + consumption、適合穩定 workload、中小 burst 不划算
- Aurora DSQL：consumption-based、burst 友善、長期穩定 workload 累計可能比 Spanner 高

### 回路徑

- [9.6 容量規劃模型](/backend/09-performance-capacity/)
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 完整對比

## 邊界與整合

### 同 vendor 的其他文章

- [HLC + Raft consensus](../hlc-raft-consensus/)（軟體時鐘 vs TrueTime）
- [locality-aware schema](../locality-aware-schema/)（locality model 對比）
- [survival goals](../survival-goals/)（HA model 對比）
- [transaction retry pattern](../transaction-retry-pattern/)（application contract 重塑）

### Sibling 跨 vendor

- [Aurora vendor overview](/backend/01-database/vendors/aurora/)（async cross-region、不是 distributed SQL）
- [Spanner vendor overview](/backend/01-database/vendors/spanner/) 對照頁
- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)（單區 OLTP fallback）

### Migration playbook

- [PG → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)
- [PG → Aurora DSQL](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)

### 1.x 章節互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游
- [vendor lock-in 卡](/backend/knowledge-cards/vendor-lock-in/)
- [distributed SQL 卡](/backend/knowledge-cards/distributed-sql/)

### 何時不用本文

- single-region OLTP 已夠（90% 場景）→ 用 PostgreSQL / Aurora、不必走 distributed SQL
- 無 multi-region requirement、無跨 boundary 合規需求 → 同上
- workload 規模未撞 single-primary 寫入上限 → 走 Aurora vertical scale + read replica 即可

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（single-primary 寫入撞牆）
- [Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（Cassandra 缺口、Database Platform Team）
- [Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（合規驅動 + team size 槓桿）
- [Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)（Spanner ground truth + sizing barrier）
- [Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)（合規邊界 anti-recommendation）
- [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)（Aurora sharding 不換引擎路徑）
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- [distributed SQL 卡](/backend/knowledge-cards/distributed-sql/) / [vendor lock-in 卡](/backend/knowledge-cards/vendor-lock-in/) / [quorum 卡](/backend/knowledge-cards/quorum/)
- 官方：[Cockroach Labs Documentation](https://www.cockroachlabs.com/docs/) / [Spanner Documentation](https://cloud.google.com/spanner/docs) / [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/)
