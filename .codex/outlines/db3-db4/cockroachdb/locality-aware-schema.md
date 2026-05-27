# CockroachDB Locality-Aware Schema：regional / global table、partition by region 與 placement 配置

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力（Hard Rock concrete case 主導、F4.10）：美國 sportsbook 受 Wire Act 規範、betting data 必須在下注州內處理 → 每個營運州都要有州內運算資源。傳統路徑「每州一個獨立 silo」撞牆於跨州統一帳戶、跨州 reporting、欺詐偵測 — 玩家在 NJ 與 FL 兩州都有帳戶、統計與風控需要跨州看。Hard Rock Digital 跨 8 州（AZ / IN / TN / FL / OH / IL / NJ / VA）用 AWS Outposts 把運算放進州內、但邏輯上仍是 *一個* CockroachDB cluster — region placement 配置決定哪些 range 釘在哪個 Outpost / AWS region，合規與單一邏輯 DB 同時成立（case 觀察段「跨所有 region 一個 logical database」+ 判讀段 1）
- 讀者徵兆：「合規逼我每州一 cluster、但跨州帳戶 / 風控 / 欺詐偵測撞牆怎麼辦？」「Regional table 跟 global table 差在哪？」「`REGIONAL BY ROW` 跟 `REGIONAL BY TABLE` 怎麼選？」「Global table 為什麼讀快寫慢？」「AWS Outposts 是 latency 工具還是合規工具？」
- Case anchor: primary [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（跨 8 州單一邏輯 cluster + AWS Outposts / Local Zones / Regions 混合部署、Wire Act 合規逼出「邏輯一個 cluster + 物理跨地理 placement」拓樸創新、F4.10 / F4.13）、secondary [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（60+ multi-region cluster、最大 Gaming 48-node 跨 4 region、locality 配置直接影響 cluster 規模治理）；對照 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) Aurora 7 cluster fleet 拓樸 — Aurora 沒 row-level locality、靠 fleet 拓樸吸收合規 boundary（cluster-per-市場）、CockroachDB 靠 locality + placement 吸收（邏輯一個 cluster + range 釘到州內 Outpost）、兩種架構策略 trigger 不同（合規顆粒 + 跨 boundary 業務邏輯需求）

## 核心機制（Vendor-specific mechanism）

- 三種 table locality：
  - `REGIONAL BY TABLE`：整個 table 在指定 region、其他 region read 走 follower read
  - `REGIONAL BY ROW`：每 row 標 region、row 跟著用戶資料地理
  - `GLOBAL`：read 在每 region local（fast read）、write 強一致跨 region（slow write）、適合 reference data
- Row-level region 標記：每 row 有 `crdb_region` 隱含欄位、partition by region 自動 placement
- Locality + survival goal 互動：`REGIONAL BY ROW` + `SURVIVE REGION FAILURE` → row 本地 region 是 leaseholder、其他 region 也有 voting replica
- Follower read：non-voting replica 可 serve read（讀到稍 stale 資料）、降低 cross-region read latency
- 配置：`ALTER TABLE users SET LOCALITY REGIONAL BY ROW`、`ALTER DATABASE mydb PRIMARY REGION us-east1`
- 對應 knowledge card：[partitioning](/backend/knowledge-cards/partitioning/)（若已建）、[stale-read](/backend/knowledge-cards/stale-read/)、[data-residency](/backend/knowledge-cards/data-residency/)（若已建）
- 跟通用 sharding 差在哪：CockroachDB locality 是宣告式（不用 application 端配 shard key）、planner 自動感知 row region

## 操作流程（Operations）

- 配置 multi-region database：

```sql
ALTER DATABASE mydb PRIMARY REGION "us-east1";
ALTER DATABASE mydb ADD REGION "europe-west1";
ALTER DATABASE mydb ADD REGION "asia-northeast1";
```

- 配置 table locality：

```sql
ALTER TABLE users SET LOCALITY REGIONAL BY ROW;
ALTER TABLE config SET LOCALITY GLOBAL;
ALTER TABLE orders_us SET LOCALITY REGIONAL BY TABLE IN "us-east1";
```

- 驗證點：`SHOW LOCALITY FROM TABLE users`、`SHOW RANGES FROM TABLE users` 看 replica 分佈、query plan `EXPLAIN ANALYZE` 看是否 local read
- Application 端：寫 row 帶 `crdb_region`（INSERT INTO users (id, name, crdb_region) VALUES (...)）、或用 default `gateway_region()`
- Rollback boundary：locality 改變即時生效、Raft 自動 rebalance；無不可逆動作但 rebalance 期間 cross-region traffic 暴增

## 失敗模式（Failure modes）

- **「拆獨立 cluster 解合規但破壞業務邏輯」反模式（Hard Rock 對比 Standard Chartered 揭露、F4.10）**：直覺路徑是「合規要求資料留某地理邊界 → 每邊界開一個獨立 cluster」、但獨立 cluster 之間玩家統一帳戶、跨州 reporting、欺詐偵測會撞牆。Hard Rock 選 *邏輯一個 cluster + 物理跨州 Outpost placement* — 合規 boundary 用 region placement 表達、不是 cluster fragmentation。對比：
    - **Standard Chartered Aurora 7 cluster fleet**：銀行業跨國合規邊界、跨 cluster 業務邏輯需求弱（每市場用戶獨立、跨境統一帳戶不是核心 driver）→ 用 fleet 拓樸吸收合規可行
    - **Hard Rock Wire Act 跨州**：跨州統一帳戶 + 跨州 reporting + 欺詐偵測是核心業務需求 → 必須邏輯一個 cluster、用 locality + placement 吸收合規
    - 寫稿時引用對比要明示：兩條路徑沒有對錯、trigger 條件不同（合規顆粒 × 跨 boundary 業務邏輯需求）
- **「把 Outposts 當 latency 工具」動機誤判（F4.13、case 反直覺判讀）**：AWS Outposts 主要為「資料留某地理邊界」存在、latency 改善是 *副作用*。Hard Rock 策略段 2 明確警告「決策時先看合規驅動力、latency 改善列為 bonus」。若把 Outposts 當跨州 latency 改善工具、會在沒合規驅動的場景過度投資 — Outposts 硬體成本 + 維運複雜度遠高於純 AWS region 部署
- Global table write 太慢：global table 每次 write 跨 region quorum、p99 100ms+、用在 high-write workload 是錯配；應只用在 reference data（國家代碼、貨幣表）
- Regional by row 但 row 沒設 region：default `gateway_region()` 把 row 放在 application 連到的 region、跨 region access pattern 不對；要明確設 `crdb_region`
- Cross-region join 跑爆 latency：兩個 regional by row table join、planner 要跨 region 拉資料、p99 暴漲；要 partition by 同樣 key
- Follower read 假設 strong consistency：non-voting replica 是 *closed timestamp* 之前的 data、read-after-write 場景仍會 stale
- Data residency 違規：受監管州 / 國資料應留 boundary 內、但 application 從別 region 寫入 row 沒設 `crdb_region`、資料跑出 boundary、合規 violation（Wire Act / GDPR / 各州博彩牌照都有類似條款）
- Schema change locality：ALTER TABLE 改 locality 期間 query plan 改變、p99 短期 spike
- Case 對應根因（Hard Rock 9.C41）：bet placement / settlement / account management 都需要跨州資料存取 + 州內合規 placement、`REGIONAL BY ROW` + `crdb_region` 標州別 + region placement pin Outpost 是滿足條件的組合

## 容量與觀測（Capacity & observability）

- CockroachDB Console metric：`Range locality distribution`、`Cross-region query count`、`Follower read rate`、`Leaseholder distribution by region`
- Application metric：query latency p99 per region（local vs cross-region）、follower read hit rate
- 容量公式：cross-region traffic = global table write QPS × region count；regional by row 跨 region read = follower read rate × QPS
- 容量上限：region count（建議 ≤ 5）、global table 數量（建議只放 reference data）
- 回路徑：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 cross-region-bound vs CPU-bound、合規邊界 [data residency](/backend/knowledge-cards/data-residency/) 卡

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[CockroachDB survival goals](./survival-goals.md)（locality + survival goal 一起決定 placement）、[CockroachDB transaction retry pattern](./transaction-retry-pattern.md)（partition 降低 hot row contention）、[CockroachDB HLC + Raft consensus](./hlc-raft-consensus.md)（leaseholder 跟 locality 關係）
- 跟 Aurora Global Database 對照：Aurora 不能 row-level locality、只能 cluster-per-region；CockroachDB 一個 cluster 內 fine-grained locality
- 跟 Spanner 對照：Spanner 的 interleaved tables 跟 CockroachDB 的 regional by row 概念類似、語法不同
- Aurora DSQL / Spanner 決策樹：見 [aurora-dsql-spanner-decision-tree](./aurora-dsql-spanner-decision-tree.md)
- 1.x 章節互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)、[data residency](/backend/knowledge-cards/data-residency/) 卡
- 何時不用本文：single-region 部署、無 data residency 需求

## 寫作前置 checklist

- [ ] case anchor 確認：Hard Rock Digital 9.C41（primary、concrete case 主導 framing、跨 8 州 + Outposts + 邏輯一個 cluster）+ Netflix 9.C40（secondary、多 region locality 規模治理）+ Standard Chartered 9.C14（對照 fleet 拓樸 vs locality 兩條合規路徑）— 三 case 已備、*不再依賴合成 GDPR 場景*
- [ ] knowledge card 雙引用：[stale-read](/backend/knowledge-cards/stale-read/) + [data-residency](/backend/knowledge-cards/data-residency/)（若已建、否則建卡）
- [ ] sibling 對比：跟 Spanner interleaved tables 對照、跟 Aurora Global Database / fleet 拓樸對照（Standard Chartered 路徑）
- [ ] Framing 紀律：第一段問題情境必須是 Hard Rock Wire Act concrete case（不是合成 GDPR）；GDPR 場景可作為 secondary 應用例、不主導 framing
- [ ] Outposts 動機紀律：每處提 Outposts 必須明示「合規驅動、latency 改善為副作用」（F4.13）、避免把 Outposts 描述為「跨州延遲改善」
- [ ] 預估寫作長度：260-320 行（三種 locality + placement + Hard Rock framing + Standard Chartered 對比 + Outposts 動機釐清）
- [ ] 寫作難度：中（CockroachDB docs 充分、Hard Rock case 提供 concrete framing、case 對比 Standard Chartered 強化拓樸決策）
