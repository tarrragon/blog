# CockroachDB vs Aurora DSQL vs Spanner：撞牆訊號分型 + 跨雲、managed 成熟度、PostgreSQL wire、team size、sizing 五軸決策樹

> **Status**: L5 outline skeleton（planning artifact、非 published article）、DB4 entry point candidate（_module-outline.md D.1）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Entry point 定位**：本篇承擔 DB4 distributed SQL 選型的 reader entry point — 讀者進來時還沒決定哪個 vendor、甚至還沒釐清「我是不是該換 distributed SQL」。本篇先用「撞牆訊號分型」幫讀者識別自己屬哪條 driver path、再進三軸 vendor 對比、最後落到 team size + sizing 邊界檢查。

## 問題情境（Production pressure）

- 啟動壓力：團隊評估「全球分散式 OLTP」三選一（CockroachDB / Aurora DSQL / Spanner）、文件都說「跨 region 強一致 SQL」、看不出實際取捨；做錯選擇後遷移成本極高
- 讀者徵兆：「我是不是真該換 distributed SQL、還是 Aurora / Cloud SQL 還能撐？」「Spanner 在 Google 跑了 10 年、CockroachDB 跟 DSQL 比較新、成熟度差多少？」「我有 PostgreSQL 應用、三家相容性差在哪？」「跨雲是真的硬需求還是被 fear 推的？」「DSQL 2024 才 GA、production 風險多大？」「我團隊 50 人能不能養 self-managed CockroachDB？」「Spanner 100 pu 起跳對我中小 PG workload 划算嗎？」
- Case anchor: CockroachDB direct case [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（Aurora Postgres 1.636 M QPS 撞牆 → 換 multi-primary、PostgreSQL wire 相容降低遷移阻力、F4.1 / F4.2 / F4.4）、[9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（Cassandra eventual consistency 撐不住 transactional → 補 distributed SQL、self-managed 380+ cluster + Database Platform Team、F4.6 / F4.9）、[9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（Wire Act 合規驅動 + 50 人 tech team + Outposts 混合部署、F4.10 / F4.14）；對照 [9.C10 Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 提供 Spanner ground truth（含 sizing barrier、F3.16）、[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 提供 Aurora 受監管金融的另一條路徑、[9.C4 DraftKings Aurora financial ledger](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 提供 Aurora 內 business sharding 路徑（不換引擎）

## 撞牆訊號分型：你的 driver path 是哪一條（前置問題 0、F4 Frame 1）

讀者進來前先回答：你 *為什麼* 要評估 distributed SQL？三條 driver path 各自的訊號、適配 vendor、決策路徑都不同 — 不識別 driver path 直接比 vendor 是源頭錯誤。

- **Path A — single-primary 寫入撞牆（9.C39 DoorDash 路徑、F4.6 + F4.2）**：
    - 訊號：寫入量持續成長、Aurora / RDS / Cloud SQL primary CPU + WAL flush rate 接近上限（*轉折點不是 IOPS、是 primary CPU + WAL flush*、F4.2、DoorDash 策略段 1）
    - DoorDash concrete reference：2020-04-17 高峰 > 1.636 M QPS、multi-hour outage（觀察段表格、F4.1 case 自帶警示「這是 Aurora 撞牆痛點、不是 CockroachDB throughput claim」）
    - 適配 vendor：CockroachDB / Aurora DSQL / Spanner 都解、選擇看其他軸
    - **Scope warning**：DoorDash 沒揭露遷移後單一 CockroachDB cluster 峰值、case 警語要保留
- **Path B — eventual consistency 缺口（9.C40 Netflix 路徑、F4.6）**：
    - 訊號：原本用 Cassandra / Riak / DynamoDB eventual consistency，遇到 *5 條件並存* 需求 — multi-active topology + global consistent secondary index + global transaction + open source + SQL（Netflix 判讀段 1、5 條件 case 直接列出）
    - 具體場景：Studio Cloud Drive（強一致 metadata + 全球可寫）、Open Connect 控制平面、Spinnaker、Maestro、Gaming control plane
    - 適配 vendor：CockroachDB（open source + SQL 兩條件硬卡）、Spanner（若 GCP-only 可放鬆 open source 要求）
- **Path C — 合規驅動的地理邊界 + 跨 boundary 業務邏輯需求（9.C41 Hard Rock 路徑、F4.10）**：
    - 訊號：法規要求資料留某地理邊界（Wire Act 跨州、GDPR 跨國、各州博彩牌照）+ 業務邏輯需要跨 boundary（跨州統一帳戶 / 跨州 reporting / 欺詐偵測）
    - Hard Rock concrete reference：跨 8 州 + Outposts + 邏輯一個 cluster（觀察段表格）
    - 適配 vendor：CockroachDB（locality + placement + Outposts）、Spanner（GCP region 內 placement、無 Outposts 等效）、Aurora DSQL 跨 region 強一致但 Outpost 部署現階段未完整覆蓋
- **不該換 distributed SQL 的訊號**：single-region OLTP 已夠 + 寫入量未撞 single-primary 天花板 + 無跨 region 業務需求 + 無跨 boundary 合規需求 → PostgreSQL / Aurora 足夠、distributed SQL overhead（2-5x latency、ops 複雜度）不划算

## 核心機制（Vendor-specific mechanism）

- 三軸決策（vendor 對比軸）：
  - **軸 1 — 部署 topology**：cross-cloud / on-prem（CockroachDB）vs GCP-only（Spanner）vs AWS-only（Aurora DSQL）
  - **軸 2 — Managed 成熟度（來源分層）**：Spanner 10+ 年 Google 內部 + 外部 GA（依 9.C10 case + Google research paper、屬 vendor 公開文件 + dogfood frame）、CockroachDB 自管 + Cockroach Cloud（managed 較新，依 Cockroach Labs 公告）、Aurora DSQL 2024-05 GA（依 AWS 公告）— **Scope warning**：3 case 都沒揭露成熟度比對、本軸依 case + vendor 公開文件 + 外部知識合成、寫稿時要明示來源層次
  - **軸 3 — SQL 相容性**：CockroachDB PostgreSQL wire（*protocol-level* 相容、SQL 行為仍要 audit，F4.4）、Spanner GoogleSQL + 部分 PostgreSQL 方言、Aurora DSQL PostgreSQL（AWS managed control plane）
- **PostgreSQL 相容性 audit checklist（F4.4、DoorDash 揭露 protocol-level 相容、SQL 行為仍要驗證）**：
    - **Serializable default**：CockroachDB default SERIALIZABLE、PG default READ COMMITTED → application transaction 行為差異（細節見 [transaction-retry-pattern](./transaction-retry-pattern.md)）
    - **Retry semantics**：CockroachDB 發 `40001 serialization_failure`、application 必須包 retry loop；PG / Aurora 預設不需要
    - **Partial index**：CockroachDB 支援程度與 PG 有差異、application 用到的 partial index 要逐一驗證
    - **其他 SQL 行為**：sequence、auto-increment、stored procedure 等需 case-by-case audit
    - 寫稿時引用 DoorDash「PG wire 相容」必須加 case 警語「protocol-level 相容、SQL 行為仍要驗證」、避免讓讀者把高相容誤讀為 drop-in
- Consensus 機制差：
  - CockroachDB：HLC + Raft（軟體時鐘）
  - Spanner：TrueTime（GPS + atomic clock hardware）+ Paxos
  - Aurora DSQL：類似 Spanner 概念但 AWS 專屬 timing infra
- Pricing model 差：
  - CockroachDB self-managed：node × resource、cluster 至少 3 node
  - Cockroach Cloud / Spanner / DSQL：consumption-based（read / write / storage / network）
- **Sizing barrier 邊界（F3.16、9.C10 Spanner case 揭露）**：Spanner 100 processing unit 起跳是 *最小 footprint*、對中小 PostgreSQL workload 是 cost 邊界 — workload 月寫入若只夠 PG db.m6g.large 級別、付 Spanner 100 pu 起跳是 cost 不對。CockroachDB 最小 3 node、Aurora DSQL consumption-based 無 minimum、相對中小 workload 友善
- 對應 knowledge card：[distributed-sql](/backend/knowledge-cards/distributed-sql/)、[quorum](/backend/knowledge-cards/quorum/)、[vendor-lock-in](/backend/knowledge-cards/vendor-lock-in/)（若已建）

## 決策樹（Decision tree）

> 前置問題 0 在 *撞牆訊號分型* 段已回答（你的 driver path 是 A / B / C 哪一條）；以下進三家 vendor 對比。

- **問題 1：是否硬需求跨雲 / on-prem？**
  - Yes → CockroachDB（唯一選項；對應 9.C40 Netflix 跨 AWS region、9.C41 Hard Rock AWS Outposts 混合）
  - No → 進問題 2
- **問題 2：已在 AWS 還是 GCP 還是中立？**
  - AWS 深 → Aurora DSQL（操作模型對齊、PostgreSQL 相容）
  - GCP 深 → Spanner（10 年成熟、Google 內部驗證）
  - 中立 / 多雲 → CockroachDB（可 portable）
- **問題 3：production 風險預算？**
  - 低（金融 / 醫療）→ Spanner（最成熟）或 CockroachDB（>5 年外部 production case）
  - 中 → 三者皆可
  - 高（願意當 early adopter）→ Aurora DSQL（2024 GA）
- **問題 4：PostgreSQL 相容性是 hard requirement？**
  - Yes（既有 application）→ CockroachDB 或 Aurora DSQL（兩者都做 PG 相容、但走 audit checklist 驗證 SQL 行為）
  - No → Spanner（GoogleSQL 也可）
- **問題 5：管理負擔誰承擔？**
  - 自管 → CockroachDB（唯一可自管）
  - Managed → 都行、依雲商生態
- **問題 6：team size 是否撐得起 self-managed（F4.14、9.C41 Hard Rock + 9.C40 Netflix 揭露）**：
    - distributed SQL 的 ops 槓桿來自系統內建 Raft / placement 把「DBA 養單區、跨區 sync 養運維」工作量壓進系統內 — Hard Rock 50 人 tech team 估「若用 PostgreSQL 需多加 10-20 工程師」（觀察段表格 + 策略段 4）
    - **Case 自帶警示**：「省了 10-20 工程師」是 *機會成本*（沒招那麼多 DBA）、*不是* 節省支出（已 hire 後解雇）— 寫稿時引用必須明示口徑、避免讓讀者誤解為「上 CockroachDB 可裁員」
    - Self-managed 規模化的另一極：Netflix 養 380+ cluster 需要 *專屬 Database Platform Team*（含 backup / upgrade / incident response / capacity review、F4.9）。沒這量級團隊直接 self-host 大規模 cluster 是 ops 自殺、Cockroach Cloud 才是合理路徑
    - 決策軸：team size 小（< 100 人 tech team）→ Cockroach Cloud / Spanner / DSQL（managed）優先；team size 大且有專屬 DB platform team → self-managed CockroachDB 可考慮
- **問題 7：sizing 是否撐得起 vendor minimum（F3.16）**：
    - Spanner 100 processing unit 起跳對中小 PG workload 是成本門檻、月寫入 < 某 baseline 時付 Spanner 起跳費不划算
    - 中小 workload 但需 multi-region 強一致 → CockroachDB 3 node 起 / Aurora DSQL consumption-based 較友善
    - 大 workload（已過 single-primary 撞牆訊號）→ 三家皆可、進問題 1-6 再篩

## 失敗模式（Failure modes）

- 過度 fear AWS / GCP lock-in：90% 公司其實 single-cloud、跨雲是想像中需求；選 CockroachDB 付 portability premium 卻沒實際 multi-cloud 部署
- 低估 DSQL 成熟度風險：2024-05 GA、production case 少、邊界 case 文件不全、early adopter 才適合
- Spanner 假設 PostgreSQL 全相容：Spanner PostgreSQL interface 是子集、部分 PostgreSQL feature 不支援、應用 migration 仍需 audit
- **Self-managed CockroachDB 低估 ops cost（9.C40 Netflix concrete reference、F4.9）**：Raft / backup / upgrade / monitoring 自管比 PostgreSQL 複雜、DBA bandwidth 沒到位變 disaster。Netflix 養 380+ cluster 需要 *專屬 Database Platform Team* — 含 backup、upgrade、incident response、capacity review。沒這量級團隊直接 self-host 380 cluster 是 ops 自殺、Cockroach Cloud 才是合理路徑。判讀訊號：「self-managed cluster 數量 vs 平台團隊規模」轉折點 case 沒講要謹慎、寫稿時不可宣稱具體閾值
- 用 distributed SQL 解 single-region OLTP：90% 場景 PostgreSQL / Aurora 夠用、distributed SQL overhead 是 2-5x latency
- 合規邊界誤判：受監管市場可能不能用任何跨境 distributed SQL（Standard Chartered 模式）、要拆每市場獨立 cluster；或反過來、合規顆粒小（跨州 vs 跨國）+ 跨 boundary 業務邏輯需求高（跨州統一帳戶）時、Standard Chartered fleet 拓樸不適合、需走 Hard Rock locality + placement（細節見 [locality-aware-schema](./locality-aware-schema.md)）
- Sizing barrier 誤判（F3.16）：中小 PG workload 直接套 Spanner 100 pu 起跳、付的是不必要的 minimum cost
- Team size 誤判（F4.14）：把「省 10-20 工程師」當已 hire 後可裁員的節省支出、實際是 *機會成本*（沒招那麼多 DBA）；上 CockroachDB 不代表可裁掉現有 DBA
- Case 對應根因：為什麼 Standard Chartered 用 Aurora（single-region per 市場）而非 Aurora DSQL（multi-region）、合規邊界比技術選型優先

## 容量與觀測（Capacity & observability）

- 三家共同 metric：write QPS、cross-region latency、storage growth、replica lag
- CockroachDB Console 暴露 Raft / range / leaseholder（observability 細）
- Spanner / DSQL 是 managed、metric 經 GCP Cloud Monitoring / AWS CloudWatch（observability 黑箱程度高）
- 容量公式：write QPS × replication factor × cross-region latency = required node / capacity
- Cost signal：三家定價模式不同、cross-region traffic 對 cost 影響都大
- 回路徑：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 完整對比

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[CockroachDB HLC + Raft consensus](./hlc-raft-consensus.md)（軟體時鐘 vs TrueTime）、[CockroachDB locality-aware schema](./locality-aware-schema.md)（locality model 對比）、[CockroachDB survival goals](./survival-goals.md)（HA model 對比）
- Sibling 跨 vendor：[Aurora Global Database](../aurora/global-database-multi-region.md)（async cross-region、不是 distributed SQL）
- Migration playbook：[PG → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)、[PG → Aurora DSQL](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)
- 1.x 章節互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游、[Spanner vendor](/backend/01-database/vendors/spanner/) 對照頁
- 何時不用本文：single-region OLTP 已夠、無 multi-region requirement、PostgreSQL / Aurora 足夠

## 寫作前置 checklist

- [ ] case anchor 確認：CockroachDB 三家 direct case（DoorDash / Netflix / Hard Rock）已備、Spanner 9.C10 + Standard Chartered 9.C14 + DraftKings 9.C4 對照已備、entry point 升級條件齊
- [ ] knowledge card 雙引用：[distributed-sql](/backend/knowledge-cards/distributed-sql/) + [vendor-lock-in](/backend/knowledge-cards/vendor-lock-in/)（若已建）
- [ ] sibling 對比：撞牆訊號分型（3 path）+ 7 個問題決策樹 + 失敗模式 + 三家具體 case ground truth
- [ ] **Scope warning 紀律**：軸 2 managed 成熟度比對、Spanner sizing barrier、PG 相容性 audit 都屬合成 / vendor 文件來源、寫稿時明示來源層次；team size 引用 Hard Rock case 必須帶 case 自帶警示（機會成本 vs 節省支出）
- [ ] SSoT 對應：本篇承擔 CockroachDB cluster boundary 顆粒（per-app vs shared cluster）主寫角色；[hlc-raft-consensus](./hlc-raft-consensus.md) cross-link 不展開
- [ ] 預估寫作長度：320-400 行（entry point 規格、撞牆訊號分型 3 path + 7 軸決策樹 + audit checklist + 失敗模式 + 來源分層紀律）
- [ ] 寫作難度：中高（三家文件公開、但要避免 marketing-y 比較、要落到具體成本與失敗模式、且 entry point 角色要求清晰 reader journey）
