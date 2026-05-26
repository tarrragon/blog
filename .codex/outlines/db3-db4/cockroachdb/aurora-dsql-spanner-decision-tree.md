# CockroachDB vs Aurora DSQL vs Spanner：跨雲、managed 成熟度、PostgreSQL wire 三軸決策樹

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊評估「全球分散式 OLTP」三選一（CockroachDB / Aurora DSQL / Spanner）、文件都說「跨 region 強一致 SQL」、看不出實際取捨；做錯選擇後遷移成本極高
- 讀者徵兆：「Spanner 在 Google 跑了 10 年、CockroachDB 跟 DSQL 比較新、成熟度差多少？」「我有 PostgreSQL 應用、三家相容性差在哪？」「跨雲是真的硬需求還是被 fear 推的？」「DSQL 2024 才 GA、production 風險多大？」
- Case anchor: CockroachDB direct case 用 [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（PostgreSQL wire 相容降低遷移阻力、Aurora 撞牆推力）、[9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（跨雲 / on-prem 部署的 fleet 規模證據）、[9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（AWS Outposts 混合部署的合規路徑）；對照 [9.C10 Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 提供 Spanner ground truth、[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 提供 Aurora 受監管金融的另一條路徑

## 核心機制（Vendor-specific mechanism）

- 三軸決策：
  - **軸 1 — 部署 topology**：cross-cloud / on-prem（CockroachDB）vs GCP-only（Spanner）vs AWS-only（Aurora DSQL）
  - **軸 2 — Managed 成熟度**：Spanner 10+ 年 Google 內部 + 外部 GA、CockroachDB 自管 + Cockroach Cloud（managed 較新）、Aurora DSQL 2024-05 GA（最新）
  - **軸 3 — SQL 相容性**：CockroachDB PostgreSQL wire（高相容）、Spanner GoogleSQL + 部分 PostgreSQL 方言、Aurora DSQL PostgreSQL（AWS managed control plane）
- Consensus 機制差：
  - CockroachDB：HLC + Raft（軟體時鐘）
  - Spanner：TrueTime（GPS + atomic clock hardware）+ Paxos
  - Aurora DSQL：類似 Spanner 概念但 AWS 專屬 timing infra
- Pricing model 差：
  - CockroachDB self-managed：node × resource、cluster 至少 3 node
  - Cockroach Cloud / Spanner / DSQL：consumption-based（read / write / storage / network）
- 對應 knowledge card：[distributed-sql](/backend/knowledge-cards/distributed-sql/)、[quorum](/backend/knowledge-cards/quorum/)、[vendor-lock-in](/backend/knowledge-cards/vendor-lock-in/)（若已建）

## 決策樹（Decision tree）

- **問題 1：是否硬需求跨雲 / on-prem？**
  - Yes → CockroachDB（唯一選項）
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
  - Yes（既有 application）→ CockroachDB 或 Aurora DSQL
  - No → Spanner（GoogleSQL 也可）
- **問題 5：管理負擔誰承擔？**
  - 自管 → CockroachDB（唯一可自管）
  - Managed → 都行、依雲商生態

## 失敗模式（Failure modes）

- 過度 fear AWS / GCP lock-in：90% 公司其實 single-cloud、跨雲是想像中需求；選 CockroachDB 付 portability premium 卻沒實際 multi-cloud 部署
- 低估 DSQL 成熟度風險：2024-05 GA、production case 少、邊界 case 文件不全、early adopter 才適合
- Spanner 假設 PostgreSQL 全相容：Spanner PostgreSQL interface 是子集、部分 PostgreSQL feature 不支援、應用 migration 仍需 audit
- Self-managed CockroachDB 低估 ops cost：Raft / backup / upgrade / monitoring 自管比 PostgreSQL 複雜、DBA bandwidth 沒到位變 disaster
- 用 distributed SQL 解 single-region OLTP：90% 場景 PostgreSQL / Aurora 夠用、distributed SQL overhead 是 2-5x latency
- 合規邊界誤判：受監管市場可能不能用任何跨境 distributed SQL（Standard Chartered 模式）、要拆每市場獨立 cluster
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

- [ ] case anchor 確認：等 C2 agent 補 CockroachDB direct case；現有 Spanner case 跟 Standard Chartered Aurora 對照足夠撐三軸決策
- [ ] knowledge card 雙引用：[distributed-sql](/backend/knowledge-cards/distributed-sql/) + [vendor-lock-in](/backend/knowledge-cards/vendor-lock-in/)（若已建）
- [ ] sibling 對比：5 個問題決策樹 + 5 個失敗模式 + 三家具體 case ground truth
- [ ] 預估寫作長度：260-320 行（三家對比 + 5 軸決策樹 + 失敗模式密度高）
- [ ] 寫作難度：中高（三家文件公開、但需要避免 marketing-y 比較、要落到具體成本與失敗模式）
