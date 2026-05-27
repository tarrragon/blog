---
title: "Migration Playbook：Cloud SQL for PostgreSQL → Cloud Spanner"
date: 2026-05-27
description: "Cloud SQL → Spanner 是 paradigm shift 級遷移、不是 drop-in。本 playbook 走 6 規格面 Driver / Diff / Phase / Evidence / Cutover / Cleanup：Driver 段明示 sizing barrier（100 pu 起跳）跟 < 50ms write latency 兩條 no-go；Diff 段加 sizing / cost 第 7 規格面；Phase 0 含 sizing audit；Evidence 段補 cost crossover 報告；對照 9.C10 Google internal dogfood 邊界跟 Standard Chartered 受監管 banking case"
weight: 33
tags: ["backend", "database", "spanner", "global-sql", "migration", "playbook", "postgresql", "cloud-sql", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 [migration](/backend/knowledge-cards/migration/) playbook。走 [vendor-article-spec](/backend/01-database/vendor-article-spec/) Migration Playbook 規格 + [migration-playbook-methodology](/posts/migration-playbook-methodology/) Type E（paradigm shift）。每階段切換用 [migration gate](/backend/knowledge-cards/migration-gate/) 把關 — Evidence 段列的證據是 gate 通過條件、不是 nice-to-have。

---

## Driver：為什麼遷、什麼條件不該遷

### 啟動壓力

single-region Cloud SQL PostgreSQL primary 觸到容量上限（connection、write throughput、storage IOPS、region 故障風險）、產品要求跨 region active-active write、external consistency 是契約而非 nice-to-have。讀者要先確認自己面對的是「real 跨 region write residency」、不是「想用更強的技術」 — driver 段的核心責任是排除空泛動機。

### 主要 driver 候選

- **Global write residency**：用戶分散全球、各地寫入本地 region、跨 region 一致性是產品要求
- **External consistency 對帳契約**：跨 region 交易順序錯誤會導致對帳爆炸（金融、計費、ticketing）
- **單 primary 容量天花板**：Cloud SQL 最大 instance 仍撐不住、應用層 sharding 是大工程
- **跨 region read latency**：read 從各地直接打本地 replica、Cloud SQL read replica 受 single-primary 寫入 throughput 限制

### No-go condition（基礎）

流量集中單 region、跨 region 只是 DR 需求 → 維持 Cloud SQL + read replica + cross-region async DR 更便宜。這條 no-go 不複雜、但團隊常被 marketing 推著跳過 — 在自家 traffic dashboard 上 audit 一遍「write 來自哪些 region、各占比多少」、若 90%+ 來自單 region、Spanner 沒有 benefit。

### No-go condition（sizing barrier）

小 / 中型 PostgreSQL workload 的成本門檻 — Spanner 早期最小單位 100 processing units（≈ 1 node）對中小負載偏貴、過去是 sizing barrier；2021+ 推出 100 pu 起跳的 granular sizing 後雖然可從小開始、但 100 pu × per-pu monthly cost 加上跨 region replication 仍可能比 Cloud SQL HA 設定貴數倍。

**來源 9.C10「判讀」段第 3 點**：Spanner 早期 100 pu 起跳是 sizing barrier、後來推出 granular sizing 才讓中小負載可從小開始。**Dogfood 邊界明示**：9.C10 case 揭露的 sizing 結構是 Google 內部 dogfood 的 capacity 規劃語言、不是 customer-facing pricing 承諾；客戶實際成本要看當期 Spanner pricing + region + replication config。

觸發 sizing no-go 的條件：

| 信號                          | 判讀                                             |
| ----------------------------- | ------------------------------------------------ |
| workload row count < 數百萬   | 100 pu 對這個資料量過 over-provision             |
| QPS < 1000                    | 100 pu 容量遠超實際 traffic、cost / QPS ratio 高 |
| 單 region 即可滿足合規        | 跨 region replication cost 是純浪費              |
| Cloud SQL HA 設定已 cover SLA | 升 Spanner 沒 marginal benefit                   |

觸發任一條 → 強烈建議走 Cloud SQL HA、不升 Spanner。判讀時要把 Cloud SQL HA cost vs Spanner 100 pu cost 對比清楚、避免讀者「想用新技術」而升級。

### No-go condition（應用層延遲容忍）

應用層延遲容忍 < 50ms write 的 workload 不該升 Spanner — 跨 region Spanner write 在物理光速硬限下達 100-200ms（[consistency-models-comparison](../consistency-models-comparison/) 的 cross-region quorum 段）。延遲敏感 workload 升級後會在 p99 直接撞牆、回退時資料已經寫進 Spanner、roll back 成本巨大。

**來源 9.C10「判讀」段第 2 點 + 「策略」段第 3 點**：「external consistency 必須等多區 quorum、跨洲交易延遲可達 100-200ms」。**Dogfood 邊界明示**：9.C10 揭露的數量級是 Google internal observation、客戶實際 latency 隨 voting region 配置變化、引用時要附條件。

觸發 latency no-go 的場景：

- 實時報價系統（毫秒級回應）
- 高頻交易（HFT）
- 遊戲 leaderboard 寫入
- 低延遲 OLTP（金融下單、支付路由）

觸發任一條 → 強烈建議走 Cloud SQL 單 region、或考慮把 *跨 region 一致性需求* 重新審視（是否真的需要強一致、能不能改 event-driven async reconcile）。

### 替代方案排除

- **Aurora DSQL**：AWS 生態、若團隊在 GCP、跨雲不合
- **CockroachDB**：要自管或想 PostgreSQL wire 但不選 GCP 託管時可考慮、本 playbook 不對照
- **Citus on Cloud SQL**：multi-region write 不是強項、不解 cross-region external consistency 需求

### Case anchor + dogfood 邊界

**無強 customer case**。9.C10 是 Google 內部 dogfood、不是公開遷移 case；本 playbook 用 Spanner overview 的 PostgreSQL dialect 路徑 + 官方 migration guide + 通用 pattern。引用時必須明示「9.C10 揭露的線性 scaling / line-rate 設計目標是 Spanner 設計依據、不等於客戶遷移後可獲得的 capacity」。

對照 case：[9.C14 Standard Chartered Aurora 受監管 banking](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 雖然是 Aurora、不是 Spanner、但揭露「受監管 OLTP 遷移要算合規 lead time」「資料駐留限制 = 容量規劃 per-市場」這兩條結論在 Spanner 遷移同樣適用。讀者若是受監管產業、跨 region instance config 還要疊上 voting region 是否落在合規市場的 audit。

## Diff Audit（6 規格面 + sizing / cost 第 7 面）

### Schema diff

PostgreSQL DDL → Spanner PostgreSQL dialect 對照：

| PostgreSQL 特性          | Spanner 對應                           | 動作                                           |
| ------------------------ | -------------------------------------- | ---------------------------------------------- |
| `SERIAL`                 | bit-reversed sequence                  | 改 primary key 策略、避免 hot split            |
| `JSONB`                  | `JSON` type                            | 大部分相容、複雜 path query 重寫               |
| `ARRAY`                  | `ARRAY`                                | OK                                             |
| `PARTITION BY`           | 不直接支援                             | 改成 interleaved table 或單表                  |
| `FOREIGN KEY`            | 保留 FK constraint + 考慮 INTERLEAVE   | parent-child access pattern 改 interleaved     |
| `B-tree INDEX`           | OK                                     | 直接遷                                         |
| `GIN / GiST INDEX`       | 不支援                                 | 用 `STORING` column 取代部分需求、其餘改應用層 |
| `CHECK constraint`       | 部分支援（time-sensitive、查最新文件） | audit 每條 constraint                          |
| `UDF / stored procedure` | 少數支援                               | 改應用層或 client-side compute                 |
| `TRIGGER`                | 不支援                                 | 改 application 層或 Spanner change streams     |

interleaved table 設計參考 [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)。讀者要在 schema audit 階段就決定哪些 parent-child 該 interleave、避免後悔成本。

### Operational diff

| 維度            | Cloud SQL                    | Spanner                      |
| --------------- | ---------------------------- | ---------------------------- |
| 基礎架構        | VM-based                     | API-based                    |
| 認證            | postgres user / role         | IAM role / service account   |
| 備份            | pg_dump / pgBackRest         | point-in-time backup（PITR） |
| 監控            | postgres-flavor（pg_stat_*） | Cloud Monitoring `spanner.*` |
| Connection pool | PgBouncer                    | SDK 內 gRPC pool             |
| Vacuum          | 必要                         | 不存在（MVCC 機制不同）      |
| Replication lag | 需監控                       | 不存在 single-primary 概念   |

不再需要的 Cloud SQL 責任：vacuum、autovacuum tuning、connection pool（PgBouncer）、replication lag 監控、Patroni HA。

新增 Spanner 責任：processing unit capacity 預測、TrueTime ε 觀測（[truetime-api-depth](../truetime-api-depth/)）、long-running schema operation 跟蹤、IAM 細粒度權限。

### Paradigm diff

從 single-primary OLTP → 跨 region distributed SQL：

- transaction commit latency：< 5ms → 50-200ms（跨洲）
- external consistency 是 default（不再是 isolation level 選擇題）
- transaction 上限：Cloud SQL 無硬限 → Spanner 10s timeout、要重構成短交易
- read consistency：default eventual → default strong、需顯式選 bounded staleness

詳細 consistency model 差異看 [consistency-models-comparison](../consistency-models-comparison/)。

### Component diff

退役：

- PgBouncer / pgcat（connection pool）
- Cloud SQL HA / Patroni cluster
- pgBackRest（備份外掛）
- Citus extension（若有用）
- 各種 postgres extension（時間敏感、逐個 audit 是否 Spanner 支援等效）

新增：

- Spanner client library（Go / Java / Node / Python）
- Dataflow（用於 bulk export-import）
- Datastream / Database Migration Service（用於 CDC catch-up）
- Spanner Studio（query UI）

### Application diff

| 維度                        | Cloud SQL（PostgreSQL client）       | Spanner                                                  |
| --------------------------- | ------------------------------------ | -------------------------------------------------------- |
| ORM                         | 全 PG ORM 相容                       | PostgreSQL dialect 相容部分 ORM、查最新 dialect 支援列表 |
| Connection model            | process-per-connection（postgres）   | stateless gRPC client（SDK 內 pool）                     |
| Transaction model           | 可長交易                             | 10s timeout、需短交易                                    |
| Timestamp 使用              | app 內 `now()` / `CURRENT_TIMESTAMP` | 改用 `PENDING_COMMIT_TIMESTAMP` sentinel                 |
| Cursor / prepared statement | 全支援                               | 部分支援、查 SDK 文件                                    |
| Stored procedure            | 全支援                               | 少數支援、業務邏輯改應用層                               |

ORM 兼容性是 time-sensitive claim — JPA / Hibernate / SQLAlchemy 在 Spanner PostgreSQL dialect 上的行為隨 dialect 版本演進、實作前查最新 vendor docs。讀者要把 ORM 兼容測試放 Phase 0、不能假設「PostgreSQL ORM 直接搬到 Spanner」。

### Data topology diff

- Single primary（write）+ read replica → multi-region voting + read-only replica
- Primary key 設計：避免單調遞增（SERIAL）造成 hot split、改 UUID 或 bit-reversed
- Partition：PostgreSQL declarative partition → Spanner 不需要顯式 partition（自動 split）

### Sizing / cost diff（第 7 規格面）

| 維度                  | Cloud SQL                                              | Spanner                                                         |
| --------------------- | ------------------------------------------------------ | --------------------------------------------------------------- |
| 計費單位              | instance class（vCPU / RAM）+ storage IOPS + HA add-on | 100 processing units 起跳 ≈ 1 node                              |
| 起跳成本              | 小型 instance 月成本可控（小型 HA $50-200/月）         | 100 pu × per-pu monthly rate、月成本是 Cloud SQL 小型 HA 的數倍 |
| Storage               | 獨立計費（GB / month）                                 | 含在 node count 內、無單獨 storage charge                       |
| Throughput cap        | 隨 instance class                                      | 隨 pu 線性擴展                                                  |
| 跨 region replication | 額外 read replica cost                                 | 含在 multi-region instance config 內                            |
| Egress                | 跨 region 額外                                         | 跨 region 額外                                                  |

觸發 sizing audit 的時機：workload 行數、QPS、跨 region 需求都明確後、把「Cloud SQL HA monthly bill」對「Spanner 100 pu × monthly rate + egress」做 cost crossover 分析、無法 cost crossover 證明 → 不升。

Cost crossover 不是「Spanner 成本必須低於 Cloud SQL」、是「Spanner 多付的成本要對應到具體 benefit」：

- 若 benefit 是 multi-region write residency、Spanner 多付的 cost 換得跨 region 一致性 — 對齊
- 若 benefit 只是「更新的技術」、Spanner 多付的 cost 沒對應產品價值 — 不升

### Type 判定

**Type E（paradigm shift）**、不是 drop-in。schema / app / operation / data topology / cost 五軸都動、不能用 Type B（drop-in）思路規劃 phase。詳細 type 判定方法看 [migration-playbook-methodology](/posts/migration-playbook-methodology/)。

## Phase Plan：9 段、每段有驗證門檻

### Phase 0 — Compatibility audit + sizing audit

跑 schema-converter（pgloader / Spanner migration tool）、列出 incompatible feature、決定哪些改 schema、哪些改 app。hot key 風險評估（SERIAL primary key、單調遞增 timestamp）。

同時跑 sizing audit：

- 估 target Spanner pu 數（基於 QPS、storage size、cross-region replication factor）
- 做 Cloud SQL HA cost vs Spanner cost crossover 分析
- 若 cost crossover 證明不出來 → halt migration、回到 driver 段重審

Phase 0 是 migration 的決策閘門 — 不過閘門就停、不浪費 Phase 1+ 的 engineering effort。

### Phase 1 — Target schema design

- interleaved table 設計（base on Phase 0 access pattern audit）
- Index 重寫（GIN / GiST 用 STORING column 替代、其他用 B-tree）
- Primary key 反序（避免 hot split）
- Storing column 選擇（trade-off：query latency vs index size）

Output 是 target DDL、跟原 PostgreSQL schema 並排 diff 文件、給 application 團隊審。

### Phase 2 — Application dual-target preparation

- 抽象 DB layer（repository pattern、避免直接呼 SQL）
- SDK 並存（go-pg + Spanner client）
- Feature flag 控制讀寫路徑（read-from-pg / read-from-spanner / dual-write）
- Transaction 模式 audit（長交易拆短）

### Phase 3 — Bulk initial load

Cloud SQL → Cloud Storage（CSV / Avro）→ Dataflow → Spanner。Row count + checksum 驗證、column-level diff sample。

### Phase 4 — CDC catch-up

Datastream from Cloud SQL → Dataflow → Spanner。Replication lag < 1s 為前進門檻、sustained 24h。

### Phase 5 — Shadow read

Production read 同時打 Cloud SQL 跟 Spanner、diff log 異常。至少 7 天觀察、divergence rate < 0.1%、p99 latency Spanner < 1.5x Cloud SQL。

### Phase 6 — Dual write

Cloud SQL 為 source-of-truth、Spanner 為 mirror。偵測 dual write divergence、評估是否提早升 source-of-truth。

### Phase 7 — Cutover

read-only window（< 5 min）→ 最後 catch-up → switch source-of-truth → cutover application write。

### Phase 8 — Cleanup

退役 Cloud SQL primary、保留 backup、清 PgBouncer / Patroni / 監控 dashboard。

### Stage 0 variant 規劃

若 read-only window 不可接受（24/7 不能停機的金融 / 醫療系統）、Phase 6 dual write 期間做 conflict resolution（last-writer-wins + manual reconcile）、進入 fail-forward 模式、不走 read-only cutover。

## Evidence：每階段驗證材料

| Phase   | Evidence                                                                                                                                                           |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Phase 0 | incompatible feature 清單、預估改動 SP、hot key 風險 row count、**sizing audit 報告**（target pu 數估算 + Cloud SQL HA vs Spanner cost crossover 月 / 年成本對比） |
| Phase 1 | DDL diff report、預估 backfill 時間（基於 row count + Spanner 文件）                                                                                               |
| Phase 3 | row count 對齊、column-level checksum、payload sample diff                                                                                                         |
| Phase 4 | CDC lag < 1s sustained 24h、error rate < 0.01%                                                                                                                     |
| Phase 5 | shadow read divergence rate < 0.1%、p99 latency Spanner < 1.5x Cloud SQL                                                                                           |
| Phase 6 | dual write divergence < 0.01%、reconcile queue 不積壓                                                                                                              |
| Phase 7 | cutover window 內 write 一致性、回到 Phase 6 的條件（rollback path）                                                                                               |

**Cost crossover 報告**（Phase 0 必交付）：

```text
Item                          | Cloud SQL HA | Spanner 100 pu | Delta
------------------------------|--------------|----------------|------
Compute monthly               | $X           | $Y             | $Y-X
Storage monthly               | $A           | (included)     | -$A
Cross-region replication      | $B           | (included)     | -$B
Egress (est)                  | $C           | $C             | $0
Total monthly                 | $X+A+B+C     | $Y+C           | $Y-X-A-B
Annual                        | 12*above     | 12*above       | -
Benefit (qualitative)         | -            | multi-region write residency / external consistency | -
Crossover verdict             | -            | proceed / halt | -
```

Verdict = `proceed` 才進 Phase 1；`halt` → 回到 Driver 段重審 driver 是否成立。

所有 evidence 進 incident decision log、回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## Cutover：決策與 rollback

### Cutover window

選用戶最低流量時段、< 5 min read-only freeze、預先通知。受監管產業（對照 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)）要算合規 lead time、每市場各自審。

### Decision owner

DB lead + product lead + on-call SRE 共同 sign-off。受監管產業多加合規 owner。

### Rollback condition

- cutover 後 30 min 內 p99 write latency 持續 > SLA 2x → rollback
- error rate > 1% sustained 5 min → rollback
- 對帳系統發現 divergence > 0.1% → rollback

### Rollback 機制

保留 Cloud SQL 為 read-only mirror 14 天、Spanner 改 read-only、reverse CDC（Spanner → Cloud SQL）需事先準備。Reverse CDC 在 Phase 4-6 期間就要 dry-run 過、不能 cutover 才第一次試。

連結 [rollback-window](/backend/knowledge-cards/rollback-window/)、[rollback-condition](/backend/knowledge-cards/rollback-condition/)。

## Cleanup：退役清單跟保留責任

### 退役清單

- Cloud SQL primary instance
- PgBouncer 配置
- Patroni cluster
- pgBackRest backup job（保留歸檔 90 天、依產業合規）
- Datastream pipeline
- Dataflow job

### 監控清理

postgres-specific dashboard（exporter / wal lag / autovacuum）改成 Spanner dashboard（commit_latencies / clock_skew_ms / cpu_utilization_by_priority）。

### 文件 / runbook 更新

postgres operation runbook 標記 deprecated、Spanner runbook 上線。新 runbook 含：

- DDL long-running operation 監控
- TrueTime ε 異常處理
- Cross-region instance failover drill
- Cost monitoring alert

### 稽核 / 合規

保留 final pg_dump 7 年（依產業）、incident write-back 完成、合規市場各自留檔（對照 Standard Chartered case 的 per-市場合規 lead time）。

## 邊界與整合：sibling、對照、anti-recommendation

### Sibling deep articles

- [truetime-api-depth](../truetime-api-depth/)：app 對 timestamp 假設審計（Phase 2 必讀）
- [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)：Phase 1 target schema 設計
- [consistency-models-comparison](../consistency-models-comparison/)：Phase 0 應用層一致性要求釐清、Driver 段 latency no-go 的物理硬限

### 跟其他 migration 對照

- [PostgreSQL → Aurora DSQL Migration](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)：兩者都是 PostgreSQL → distributed SQL paradigm shift、選 GCP / AWS 看生態
- [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)：通用大規模遷移方法論

### 跟 case 對照

- [9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)：dogfood case、揭露 Spanner 設計目標、不是 customer-facing capacity reference
- [9.C14 Standard Chartered Aurora banking](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)：受監管產業遷移要算合規 lead time、per-市場容量規劃

### Anti-recommendation

讀者讀完本文應該能判斷：

- 若 driver 只是「想用新技術」→ 回 Cloud SQL
- 若 workload 小（QPS < 1000、行數 < 數百萬）→ Cloud SQL HA 更划算
- 若應用層延遲容忍 < 50ms write → Cloud SQL 單 region
- 若 cost crossover 證明不出來 → halt migration、不升

Driver 是真正跨 region write residency / external consistency 對帳契約 / 單 primary 容量天花板 → 才升。Migration playbook 的目標不是把所有 Cloud SQL workload 升到 Spanner、是把「適合升」的部分用低風險路徑遷過去。
