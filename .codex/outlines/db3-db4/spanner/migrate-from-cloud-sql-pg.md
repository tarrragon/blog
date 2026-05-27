# Migration Playbook：Cloud SQL for PostgreSQL → Cloud Spanner

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/)（Migration Playbook 規格）與 [migration-playbook-methodology](/posts/migration-playbook-methodology/)。

## Driver（為什麼遷）

- 啟動壓力：single-region PostgreSQL primary 觸到容量上限（connection、write throughput、storage IOPS、region 故障風險）；產品要求跨 region active-active write、external consistency 是契約而非 nice-to-have
- 主要 driver 候選：global write residency、external consistency 對帳契約、單 primary 容量天花板、跨 region read latency
- No-go condition（基礎）：流量集中單 region、跨 region 只是 DR 需求 → 維持 Cloud SQL + read replica + cross-region async DR 更便宜
- No-go condition（sizing barrier、finding F3.16）：小 / 中型 PostgreSQL workload 的成本門檻 — Spanner 早期最小單位 100 processing units（≈ 1 node）對中小負載偏貴、過去是 sizing barrier；2021+ 推出 100 pu 起跳的 granular sizing 後雖然可從小開始、但 100 pu × per-pu monthly cost 加上跨 region replication 仍可能比 Cloud SQL HA 設定貴數倍。寫稿時要把 Cloud SQL HA cost vs Spanner 100 pu cost 對比清楚、避免讀者「想用新技術」而升級
  - 來源 9.C10「判讀」段第 3 點：Spanner 早期 100 pu 起跳是 sizing barrier、後來推出 granular sizing 才讓中小負載可從小開始
  - 觸發條件：workload 行 < 數百萬、QPS < 1000、單 region 即可滿足合規 → 強烈建議走 Cloud SQL HA、不升 Spanner
- No-go condition（應用層延遲容忍、finding F3.15）：應用層延遲容忍 < 50ms write 的 workload 不該升 Spanner — 跨 region Spanner write 在物理光速硬限下達 100-200ms（來源 9.C10「判讀」段第 2 點）、延遲敏感 workload 升級後會在 p99 直接撞牆
  - 觸發條件：實時報價 / 高頻交易 / 遊戲 leaderboard 寫入 / 低延遲 OLTP → 強烈建議走 Cloud SQL 單 region、不升 Spanner
- 替代方案排除：Aurora DSQL（AWS 生態不合）、CockroachDB（要自管或想 PostgreSQL wire 但不選 GCP 託管）、Citus on Cloud SQL（multi-region write 不是強項）
- Case anchor 跟 dogfood 邊界（finding F3.17）：缺強 customer case — 9.C10 是 Google 內部 dogfood、不是公開遷移 case；本 playbook 用 Spanner overview 的 PostgreSQL dialect 路徑 + 官方 migration guide + 通用 pattern。寫稿時要明示「9.C10 揭露的線性 scaling / line-rate 設計目標是 Spanner 設計依據、不等於客戶遷移後可獲得的 capacity」

## Diff Audit（6 規格面）

- **Schema diff**：
  - PostgreSQL DDL → Spanner PostgreSQL dialect 對照（SERIAL → bit-reversed sequence、JSONB → JSON、ARRAY → ARRAY OK、PARTITION BY → 不直接支援、要改成 interleaved 或單表）
  - FK 改成 interleaved table（若是 parent-child access pattern）
  - INDEX：B-tree OK、GIN / GiST 不支援、要用 STORING column 取代部分需求
  - 不支援的 type / feature：CHECK constraint（時間敏感 claim、查最新文件）、UDF、stored procedure（少數）
- **Operational diff**：
  - Cloud SQL：VM-based、postgres user、pg_dump / pgBackRest 備份、postgres-flavor monitoring
  - Spanner：API-based、IAM role、point-in-time backup、Cloud Monitoring `spanner.*` metric
  - 不再需要：vacuum、autovacuum tuning、connection pool（PgBouncer）、replication lag 監控
  - 新增責任：processing unit capacity 預測、TrueTime ε 觀測、long-running schema operation 跟蹤
- **Paradigm diff**：
  - 從 single-primary OLTP → 跨 region distributed SQL；transaction commit latency 從 < 5ms → 50-200ms（跨洲）
  - external consistency 是 default（不再是 isolation level 選擇題）
- **Component diff**：
  - 退役：PgBouncer、Patroni / Cloud SQL replica、pgBackRest、Citus extension（若有用）
  - 新增：Spanner client library（Go / Java / Node）、Dataflow（用於 bulk export-import）、Datastream / Database Migration Service
- **Application diff**：
  - ORM：Spanner PostgreSQL dialect 相容部分 ORM、JPA / Hibernate / SQLAlchemy 行為需逐步驗證（時間敏感、查最新 dialect 支援列表）
  - Connection model：postgres process-per-connection → Spanner stateless client（gRPC connection pool 在 SDK 內）
  - Transaction model：long-running transaction 不可（Spanner 有 10s + timeout）、需重構成短交易
  - Timestamp 使用：app 內 `now()` / `CURRENT_TIMESTAMP` 行為跟 Spanner commit timestamp 不同
- **Data topology diff**：
  - Single primary（write）+ read replica → multi-region voting + read-only replica
  - Primary key 設計：避免單調遞增（SERIAL）造成 hot split、改 UUID 或 bit-reversed
- **Sizing / cost diff（finding F3.16）**：
  - Cloud SQL：instance class（vCPU / RAM）+ storage IOPS + HA add-on、可從小型 instance 起跳、月成本可控
  - Spanner：100 processing units 起跳 ≈ 1 node、單一 node 月成本是 Cloud SQL 小型 HA 的數倍；跨 region instance config 加 quorum cost、replication 自動含在 node count 內、無單獨 storage charge 但 throughput cap 隨 pu 線性擴展
  - 觸發 sizing audit 的時機：workload 行數、QPS、跨 region 需求都明確後、把「Cloud SQL HA monthly bill」對「Spanner 100 pu × monthly rate + egress」做 cost crossover 分析；無法 cost crossover 證明 → 不升
- Type 判定：**Type E（paradigm shift）**、不是 drop-in；schema / app / operation 三軸都動

## Phase Plan

- **Phase 0 — Compatibility audit + sizing audit**：跑 schema-converter（pgloader / Spanner migration tool）、列出 incompatible feature、決定哪些改 schema、哪些改 app；hot key 風險評估（SERIAL primary key）；同時跑 sizing audit — 估 target Spanner pu 數、做 Cloud SQL HA cost vs Spanner cost crossover 分析、若 cost crossover 證明不出來 → halt migration、回到 driver 段重審
- **Phase 1 — Target schema design**：interleaved table 設計、index 重寫（GIN / GiST 替代）、primary key 反序、storing column 選擇；output 是 target DDL
- **Phase 2 — Application dual-target preparation**：抽象 DB layer、SDK 並存（go-pg + Spanner client）、feature flag 控制讀寫路徑
- **Phase 3 — Bulk initial load**：Cloud SQL → Cloud Storage (CSV/Avro) → Dataflow → Spanner；row count + checksum 驗證
- **Phase 4 — CDC catch-up**：Datastream from Cloud SQL → Dataflow → Spanner；replication lag < 1s 為前進門檻
- **Phase 5 — Shadow read**：Production read 同時打 Cloud SQL 跟 Spanner、diff log 異常；至少 7 天觀察
- **Phase 6 — Dual write**：Cloud SQL 為 source-of-truth、Spanner 為 mirror；偵測 dual write divergence、評估是否提早升 source-of-truth
- **Phase 7 — Cutover**：read-only window（< 5 min）→ 最後 catch-up → switch source-of-truth → cutover application write
- **Phase 8 — Cleanup**：退役 Cloud SQL primary、保留 backup、清 PgBouncer / Patroni / 監控 dashboard
- Stage 0 variant 規劃：若 read-only window 不可接受、Phase 6 dual write 期間做 conflict resolution（last-writer-wins + manual reconcile）、進入 fail-forward 模式

## Evidence（每階段驗證材料）

- Phase 0：incompatible feature 清單、預估改動 SP；hot key 風險 row count；sizing audit 報告（target pu 數估算 + Cloud SQL HA vs Spanner cost crossover 月 / 年成本對比）
- Phase 1：DDL diff report、預估 backfill 時間（基於 row count + Spanner 文件）
- Phase 3：row count 對齊、column-level checksum、payload sample diff
- Phase 4：CDC lag < 1s sustained 24h、error rate < 0.01%
- Phase 5：shadow read divergence rate < 0.1%、p99 latency Spanner < 1.5x Cloud SQL
- Phase 6：dual write divergence < 0.01%、reconcile queue 不積壓
- Phase 7：cutover window 內 write 一致性、回到 Phase 6 的條件（rollback path）
- 所有 evidence 進 incident decision log；回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)

## Cutover（決策與 rollback）

- Cutover window：選用戶最低流量時段、< 5 min read-only freeze、預先通知
- Decision owner：DB lead + product lead + on-call SRE 共同 sign-off
- Rollback condition：
  - cutover 後 30 min 內 p99 write latency 持續 > SLA 2x → rollback
  - error rate > 1% sustained 5 min → rollback
  - 對帳系統發現 divergence > 0.1% → rollback
- Rollback 機制：保留 Cloud SQL 為 read-only mirror 14 天、Spanner 改 read-only、reverse CDC（Spanner → Cloud SQL）需事先準備
- 連結 [rollback-window](/backend/knowledge-cards/rollback-window/)、[rollback-condition](/backend/knowledge-cards/rollback-condition/)

## Cleanup

- 退役清單：Cloud SQL primary instance、PgBouncer 配置、Patroni cluster、pgBackRest backup job（保留歸檔 90 天）、Datastream pipeline、Dataflow job
- 監控清理：postgres-specific dashboard（exporter / wal lag / autovacuum）改成 Spanner dashboard
- 文件 / runbook 更新：postgres operation runbook 標記 deprecated、Spanner runbook 上線
- 稽核 / 合規：保留 final pg_dump 7 年（依產業）、incident write-back 完成

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[truetime-api-depth](./truetime-api-depth.md)（app 對 timestamp 假設審計）、[schema-migration-interleaved-tables](./schema-migration-interleaved-tables.md)（Phase 1 target schema 設計）、[consistency-models-comparison](./consistency-models-comparison.md)（Phase 0 應用層一致性要求釐清）
- 跟 [PostgreSQL → Aurora DSQL Migration](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/) 對照、兩者都是 PostgreSQL → distributed SQL paradigm shift
- 跟 1.x 章節：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- Anti-recommendation：若 driver 只是「想用新技術」、回 Cloud SQL；driver 是真正跨 region write residency 才升

## 寫作前置 checklist

- [ ] case anchor 確認：*無強 customer case*、9.C10 是 Google internal dogfood 不是公開遷移 case；用官方 migration guide + 通用 pattern；若要列 Sharechat / Blockchain.com 等 customer case 當間接 evidence、要先回 9.C 案例庫 verify 原文細節（不在本批 F3 audit 範圍、寫稿時用要重 audit）
- [ ] Sizing barrier 明示（finding F3.16）：Spanner 100 pu 起跳對中小 PG workload 的 cost barrier；No-go condition 段必須含「cost crossover 證明不出來 → 不升」
- [ ] 跨 region latency no-go 明示（finding F3.15）：應用層延遲容忍 < 50ms write 不升 Spanner；跨 region write 100-200ms 數量級要在 Driver 段就明示
- [ ] Dogfood 邊界明示（finding F3.17）：9.C10 line-rate scaling 是設計目標證據、不是客戶可獲得 capacity；任何 9.C10 數字引用都要附這條邊界
- [ ] knowledge card 雙引用：rollback-window、rollback-condition、external-consistency
- [ ] sibling 對比：PG → Aurora DSQL、PG → CockroachDB
- [ ] 預估寫作長度：400-470 行（migration playbook 結構完整、6 規格面 + phase 9 段 + cutover/cleanup + sizing audit 段）
