# CockroachDB Locality-Aware Schema：regional / global table、partition by region 與 placement 配置

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：global SaaS 用 CockroachDB 跨 region 部署、歐洲用戶查詢卻 latency 100ms+（資料在美國 region）、要把資料 partition 到用戶 local region 但 query 又要保證強一致
- 讀者徵兆：「Regional table 跟 global table 差在哪？」「Partition by region 後 cross-region query 還能 join 嗎？」「`REGIONAL BY ROW` 跟 `REGIONAL BY TABLE` 怎麼選？」「Global table 為什麼讀快寫慢？」
- Case anchor: primary [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（60+ multi-region cluster、最大 Gaming 48-node 跨 4 region、locality 配置直接影響 cluster 規模治理）、secondary [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（跨 8 州單一邏輯 cluster + AWS Outposts、Wire Act 合規逼出 row-level locality 配置）

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

- Global table write 太慢：global table 每次 write 跨 region quorum、p99 100ms+、用在 high-write workload 是錯配；應只用在 reference data（國家代碼、貨幣表）
- Regional by row 但 row 沒設 region：default `gateway_region()` 把 row 放在 application 連到的 region、跨 region access pattern 不對；要明確設 `crdb_region`
- Cross-region join 跑爆 latency：兩個 regional by row table join、planner 要跨 region 拉資料、p99 暴漲；要 partition by 同樣 key
- Follower read 假設 strong consistency：non-voting replica 是 *closed timestamp* 之前的 data、read-after-write 場景仍會 stale
- Data residency 違規：歐洲用戶資料應留歐洲、但 application 從 us-east1 寫入 row 沒設 region、資料跑去美國、GDPR 違規
- Schema change locality：ALTER TABLE 改 locality 期間 query plan 改變、p99 短期 spike
- Case 對應根因：global SaaS 為什麼 user table 用 REGIONAL BY ROW、config table 用 GLOBAL、order_history table 用 REGIONAL BY TABLE per region

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

- [ ] case anchor 確認：等 C2 agent 補；無 case 時用合成 global SaaS user table 範例（GDPR 合規場景）
- [ ] knowledge card 雙引用：[stale-read](/backend/knowledge-cards/stale-read/) + [data-residency](/backend/knowledge-cards/data-residency/)（若已建、否則建卡）
- [ ] sibling 對比：跟 Spanner interleaved tables 對照、跟 Aurora Global Database cluster-per-region 對照
- [ ] 預估寫作長度：240-280 行（三種 locality + placement + 合規場景）
- [ ] 寫作難度：中（CockroachDB docs 充分、合規場景具體、case 缺時合成 GDPR + financial reference data 場景）
