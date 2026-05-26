# MongoDB Aggregation Pipeline Optimization：stage 順序、index 配合與 memory 邊界

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 報表 pipeline 上線時 200ms、半年後資料量翻倍變 8s、加 index 沒用；profiler 顯示 stage 之間在 memory 累積上百 MB temp data
- 「OLTP collection 上跑 analytical query」的混合 workload：把 `$group + $lookup + $sort` 接成長 pipeline、aggregation 把整個 working set 從 cache 擠走
- Sharded cluster 上跑 cross-shard aggregation：`$group` / `$sort` 必須在 mongos 合併、mongos 變單點瓶頸
- `$lookup` 出現在 hot path：每筆 input doc 都要去另一個 collection 查、嚴格意義上是 N+1
- 讀者徵兆：`db.serverStatus().metrics.aggStageCounters` 飆、`executionStats.executionTimeMillis` 跟 doc 數線性增長、profiler 報 `usedDisk: true`、aggregation OOM kill `QueryExceededMemoryLimitNoDiskUseAllowed`
- Case anchor: needs new case（report dashboard 因 aggregation 不收斂導致 primary 撐爆 + degrade incident）；側面引用 [Microsoft 365 Cosmos DB analytics](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（從 MongoDB 把 analytics 分離出來的 driver）

## 核心機制（Vendor-specific mechanism）

- Pipeline 是 stage 序列：每個 stage 接 stream of document、產出 stream of document；stage 順序直接決定後續 stage 處理量
- Optimizer rewrite：MongoDB 會自動把 `$match` / `$project` 往前推、把 `$sort + $limit` 合併成 top-K，但不保證所有 case；`explain("executionStats")` 看 rewrite 後的 effective pipeline
- Index 配合：pipeline 的 *第一個 stage* 若是 `$match` 或 `$sort`、且能對到 index、就走 IXSCAN；中間 stage 都是 in-memory stream，沒 index 概念
- Memory 邊界：每個 aggregation stage 預設 100MB memory 上限、超過要 `allowDiskUse: true`（4.2+ 是預設、但 disk spill 嚴重拖慢）
- `$lookup` 在 sharded cluster：foreign collection 不能 sharded（5.0 前完全不行、5.0+ 有限放寬）；`$lookup` 本質是 nested loop join，沒 hash join / merge join
- `$facet` 平行多 pipeline：但所有 facet 共享同一個 100MB 限制
- `$merge` / `$out`：把結果寫回 collection（pre-computed view / materialized view）— 把 hot analytical query 移出 read path
- 對應 knowledge card: [hot-partition](/backend/knowledge-cards/hot-partition/)（aggregation 集中讀單 shard 的副作用）、[document-store](/backend/knowledge-cards/document-store/)、[stale-read](/backend/knowledge-cards/stale-read/)（從 secondary 跑 aggregation 的 trade-off）

## 操作流程（Operations）

- Step 1：用 `db.coll.explain("executionStats").aggregate(pipeline)` 拿到 effective pipeline 跟 stage-by-stage 時間
- Step 2：把 `$match` 推到最前 — 越早過濾、後續 stage 處理量越小
- Step 3：對 `$match` 的欄位建 compound index、確保 `executionStages` 顯示 `IXSCAN` 而不是 `COLLSCAN`
- Step 4：`$sort + $limit` 寫在一起、optimizer 才會推 top-K；單 `$sort` 不限 limit 會做 full sort
- Step 5：`$project` 早寫 — 把不需要的欄位早期 drop、減少後續 stage 處理 doc size
- Step 6：把 hot analytical pipeline 寫成 `$merge` materialized view、定時更新而不是即時跑
- Step 7：sharded cluster：避免在 hot path 用 cross-shard `$lookup` / `$group`、或把這類 query 路由到 analytical replica
- 驗證點：`executionTimeMillis` 在預期 budget 內、`totalDocsExamined / totalDocsReturned` 比值接近 1、無 `usedDisk: true`、無 stage 看到 `inMemory > 50MB`
- Rollback boundary：pipeline 改寫是 application code 變更、可以灰度；materialized view (`$merge`) 需備份 target collection 才能還原

## 失敗模式（Failure modes）

- **$lookup 在 hot path**：list page 每行去另一 collection 查、p99 隨 page size 線性增；應在 schema design 階段 denormalize 或寫成 join collection
- **`$sort` 不帶 limit + 沒 index**：全表 in-memory sort、撞 100MB 限制 → OOM 或 disk spill；`{ allowDiskUse: true }` 解 OOM 但 IO 100x 退化
- **Sharded cluster cross-shard aggregation**：`$group` 階段所有 partial result 跑到 mongos 合併、mongos memory + CPU 爆
- **Stage 順序錯**：`$lookup` 放在 `$match` 前，等於對全表都做 lookup 再過濾，每個 input doc 都觸發 lookup
- **Aggregation 把 working set 擠走**：OLTP 的 hot page 被 aggregation 的 cold scan 擠出 cache、整體 query latency 一起退化
- **`$facet` 滿載**：四個 facet 各跑大 pipeline、共享 100MB 限制立刻爆
- Anti-recommendation：報表 / BI / analytics workload 跑 MongoDB primary 是反模式；應該 (a) 設定 analytical secondary + read preference (b) 用 `$merge` 寫到 reporting collection (c) 進階用 BI Connector / data lake / 把 analytical workload 整批搬到 ClickHouse / BigQuery

## 容量與觀測（Capacity & observability）

- 關鍵 metric：aggregation operation time 分布、disk spill 次數、`opcounters.command` 中 aggregate 比例、cache eviction rate 在 aggregation 高峰時的變化
- Mongo command：`db.currentOp({ "command.aggregate": { $exists: true } })`、`db.serverStatus().metrics.aggStageCounters`、explain 帶 `executionStats`
- Profiler：`db.setProfilingLevel(1, {slowms: 200})`、看 `usedDisk` flag 跟 `numYield`
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：aggregation slow log + cache hit ratio + disk spill rate 是「analytical 壓力」的 evidence 三件套
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：用 explain executionStats 把 pipeline stage 對到瓶頸（IXSCAN 還是 COLLSCAN、in-memory 還是 disk spill、shard-local 還是 mongos merge）

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[schema design pattern](./schema-design-pattern.md)（embedded 設計可消除大部分 `$lookup`）、[shard key selection](./shard-key-selection.md)（決定 aggregation 是 shard-local 還是 cross-shard）、[replica set read preference](./replica-set-read-preference.md)（aggregation 跑 secondary 的 stale read trade-off）
- Migration playbook：analytical workload 大到不能繼續混在 MongoDB → split 出 [→ Cosmos DB MongoDB API + Synapse](/backend/01-database/vendors/mongodb/) 或 [→ DynamoDB + Athena/Glue](/backend/01-database/vendors/mongodb/)（access pattern 重設計）
- 跟 1.x 互引：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把 aggregation 列為 read-shape 的成本維度；[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 處理「OLTP + analytical 同 cluster」的反模式

## 寫作前置 checklist

- [ ] Case anchor：aggregation 跑爆 primary 的具體 incident 強烈需要新建 case（含 dashboard timestamp 對應的 cache eviction 圖）
- [ ] Knowledge card 雙引用：document-store + hot-partition + stale-read 三張都已存在
- [ ] Sibling 對比清楚：跟 PostgreSQL aggregation（CTE / window function + planner-based optimization）對比，MongoDB 是 stage stream + 手動 reorder 為主；跟 BigQuery / ClickHouse 等真 analytical engine 對比劃出邊界
- [ ] 預估寫作長度：260-320 行（stage-by-stage 解釋 + 5 個 failure mode + materialized view 操作流程）
