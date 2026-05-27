# Schema Migration Without Downtime + Interleaved Tables

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：傳統 PostgreSQL / MySQL DDL 拿 ACCESS EXCLUSIVE / metadata lock、線上跑 ALTER TABLE 動輒鎖表幾分鐘、大型 schema change 要 pt-osc / gh-ost / pg_repack 等外掛工具；Spanner 宣稱「schema change 不停機」、但團隊不知道實際機制跟邊界
- 讀者徵兆：「Spanner ALTER 真的不卡寫入嗎」「INDEX backfill 跑了 12 小時是正常嗎」「parent-child 的 INTERLEAVE IN PARENT 是什麼黑魔法」「ON DELETE CASCADE 在 interleaved table 為什麼是 storage-level 而不是 application-level」
- 真實壓力：multi-tenant SaaS 要對 100 億 row 的 orders 表加 column + 加 index、不能停機、不能讓 p99 write latency 超過 SLA
- Case anchor: 缺案例（9.C10 沒展開 schema migration 細節、且 9.C10 是 Google internal dogfood 不是 customer-facing capacity reference、finding F3.17）— 第一次寫時用通用 pattern + 官方文件 + 反向回 PostgreSQL [Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/) 對照

## 核心機制（Vendor-specific mechanism）

- Spanner schema change 的核心：DDL 是 *long-running operation*、不是同步 ALTER；TrueTime 給每次 schema change 分配一個 version timestamp、所有 read / write 用各自 transaction timestamp 對應「當下看到哪個 schema version」
- 不停機的關鍵：
  - 加 column：metadata-only 變更、瞬間生效（新 column 預設 NULL）
  - 加 NOT NULL constraint：兩階段、先加 column with default、後加 constraint
  - 加 index：背景 backfill、不阻塞 write；backfill 完才開始 serve query
- Interleaved table 的設計：parent table（如 Customer）跟 child table（如 Order）的 row 在 storage 層 *物理上交錯儲存*（child row 跟 parent row 在同一個 split）— 不是純 foreign key、是 storage layout
- Interleaved 的效果：parent + child JOIN 在同一個 split 完成、不跨 split = 不跨 Paxos group = 低延遲 transaction
- 限制：interleave 必須以 parent primary key 為 prefix、最深 7 層、ON DELETE 是 storage-level CASCADE 或 NO ACTION
- 跟通用概念差在哪：PostgreSQL FK 是 logic constraint、JOIN 由 planner 處理；Spanner interleaved 是 physical layout、JOIN cost 跟 single-table access 接近
- 對應 knowledge card：[transaction-boundary](/backend/knowledge-cards/transaction-boundary/) 跟 split / partition 概念

## 操作流程（Operations）

- 加 column：`ALTER TABLE Orders ADD COLUMN tax_amount FLOAT64;` → 透過 `gcloud spanner operations list` 觀察 long-running operation 狀態
- 加 index：`CREATE INDEX OrdersByCustomer ON Orders(customer_id);` → 拿 operation id → 用 Monitoring 看 `indexes/backfill_progress`
- 創建 interleaved table：

  ```sql
  CREATE TABLE Order (
    customer_id INT64 NOT NULL,
    order_id INT64 NOT NULL,
    ...
  ) PRIMARY KEY (customer_id, order_id),
    INTERLEAVE IN PARENT Customer ON DELETE CASCADE;
  ```

- 從 non-interleaved 改成 interleaved：*無法直接 ALTER*、需要 export → recreate → import；Cutover 計算進 migration playbook
- 驗證點：backfill 完成前 query 該 index 會 fallback 到 table scan、用 `EXPLAIN` 確認 query plan 走新 index 才算完成
- Rollback boundary：DDL 完成前可 cancel operation；完成後加 index 要 DROP、加 column 要 DROP COLUMN（同 long-running）

## 失敗模式（Failure modes）

- backfill 時間沒估：100 億 row 加 index、預期 1 小時、實際 12 小時 — 沒先用 `cost` 估 + 沒監控進度 metric
- Interleaved table 一開始沒設、後悔時要 recreate：100 億 row export-import + cutover 是大工程、不是 ALTER
- 把 interleaved 跟 FK 混為一談：interleaved 的 ON DELETE CASCADE 是 storage-level、刪 parent 自動刪 child；非 interleaved FK 要 application 或 trigger 處理
- 加 NOT NULL 一步到位：直接 `ALTER ADD COLUMN x INT64 NOT NULL` 會失敗、必須兩階段
- Schema change 期間舊 client 還在用舊 schema：TrueTime 保證 read 看到自己 timestamp 對應的 schema version、但 client SDK cache schema 過期會 retry — 沒處理會看到 transient error
- 監控盲點：DDL operation 失敗 silent fail 在 `gcloud operations describe` 才能看到、Cloud Monitoring 沒有直接 alert

## 容量與觀測（Capacity & observability）

- 必看 metric：`spanner.googleapis.com/instance/cpu/smoothed_utilization`（backfill 期間 CPU 升）、`api/api_request_count` for `ExecuteSql`、long-running operation API 的 progress
- backfill 期間的 capacity impact：DDL 跑在 background priority、但仍佔 CPU、需要在 instance 有足夠 headroom（建議 < 65% CPU baseline 才開大 backfill）
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：把 schema migration 列入 capacity buffer
- Observability evidence：backfill 開始 timestamp、operation id、predicted duration、實際 duration、CPU peak — 全進 incident decision log

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[truetime-api-depth](./truetime-api-depth.md)（schema version 也是 TrueTime timestamp）、[migrate-from-cloud-sql-pg](./migrate-from-cloud-sql-pg.md)（target schema 設計含 interleaved）
- 跟 PostgreSQL 的對照：[PostgreSQL Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/) 用 pg_repack / pt-osc workflow、Spanner 是原生支援
- Migration playbook 連結：本文是 migrate-from-cloud-sql-pg 的 phase plan「Schema redesign」階段必讀
- 跟 1.x 章節：[1.5 Schema 治理](/backend/01-database/schema-governance/)（若存在）
- Anti-recommendation：小 table（< 1M row）不需要 interleave、用 standard FK 就好；過度 interleave 7 層會把 split 變窄、反而 hot

## 寫作前置 checklist

- [ ] case anchor 確認：*無強案例*、用通用 pattern + 官方文件 + PostgreSQL 對照組；9.C10 是 Google internal dogfood 不展開 schema migration 細節（finding F3.17）
- [ ] knowledge card 雙引用：transaction-boundary、可考慮新建 storage-locality 卡（若沒既有卡）
- [ ] sibling 對比：PostgreSQL online schema change、MySQL gh-ost
- [ ] 預估寫作長度：240-300 行（schema change + interleaved table 兩主題並行、避免太細）
