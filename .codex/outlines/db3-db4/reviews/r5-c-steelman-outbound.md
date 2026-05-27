# Round 5-C：Steelman + Outbound Impact

> **Frame**：知識淵博讀者挑剔 + 跨 article 反向引用。Sample 8 篇 article × 跨章 cross-link 抽查。**只 review、不修檔**。

## Steelman 結果

Sample 8 篇：`aurora/storage-architecture` / `aurora/read-replica-scaling` / `dynamodb/on-demand-vs-provisioned` / `cockroachdb/transaction-retry-pattern` / `cockroachdb/aurora-dsql-spanner-decision-tree` / `spanner/truetime-api-depth` / `cosmosdb/mongodb-api-vs-sql-api` / `mongodb/connection-management-and-cache-layer`。

### Enumeration 窮盡度

整體紮實、但 sample 中發現 3 處 less obvious mode 漏列：

1. **`cockroachdb/transaction-retry-pattern` 失敗模式 6 條**漏「distributed deadlock × retry 互動」 — CockroachDB deadlock detection 跟 PG MVCC 不同、retry 可能跟 distributed deadlock 形成雪崩 pattern。case 沒揭露、屬通用工程議題。
2. **`cosmosdb/mongodb-api-vs-sql-api` 失敗模式 6 條**漏「TTL 行為差異」 — MongoDB TTL index vs Cosmos DB TTL on `_ts` / custom field 行為不同、production 偶見、屬 Phase 0 audit 細項。
3. **`dynamodb/on-demand-vs-provisioned` 失敗模式 6 條**漏「GSI 跟 base table mode 不一致」— GSI capacity 獨立計費、可能跟 base table mode 配錯。已 cross-link `gsi-lsi-design` 但本篇沒提醒 mode 互動。

vendor 對比表跟 decision tree 沒發現漏關鍵維度。`aurora-dsql-spanner-decision-tree` 七問題覆蓋部署 / 雲商 / 風險 / PG 相容 / 管理 / team size / sizing — 對知識淵博讀者算窮盡。

### 稻草人風險

**0 / 8 處明顯稻草人**。`on-demand-vs-provisioned` 開場「dev team 切 on-demand 不管 capacity」是真實 anti-pattern、不是稻草人；`aurora-dsql-spanner-decision-tree` 「90% 公司 single-cloud」雖無源頭、但方向 reasonable、屬 *未明示估算* 而非稻草。Anti-recommendation 段普遍 calibrate 良好（如 mongodb-api-vs-sql-api 列「純 MongoDB 投資留 Atlas」、不打 Atlas 稻草）。

### 數字 / 閾值源頭

明示處理良好（85%+ 數字標來源 / 口徑）、但 sample 中發現 5 處 *未明示通用估算*：

1. `aurora-dsql-spanner-decision-tree` **「90% 公司 single-cloud」「distributed SQL overhead 2-5x latency」** — 兩數字皆無源頭、屬通用估算、應補 scope warning。
2. `transaction-retry-pattern` 容量公式 **「avg retry 0.3 → 1300 transaction/s」** + 「conflict 100%」— 通用 illustrative 數字、未明示口徑。
3. `mongodb-api-vs-sql-api` **「MongoDB API RU 通常比 SQL API 多 10-20%」** — 標「通常」但無明示來源、屬 vendor docs / 通用估算。
4. `on-demand-vs-provisioned` 「provisioned base rate × 6-7 = on-demand rate」雖已標 scope warning、但 6-7x 倍率本身未明示是 AWS pricing observation 還是經驗值。
5. `storage-architecture` 「跨 AZ network round-trip 3-5ms」屬物理估算、未明示來源。

對比：`truetime-api-depth` 1-7ms ε 標「Spanner 2012 OSDI + 公開文件」、9.C10 2 → 4 nodes = 45K → 90K reads 標「dogfood、不是 customer-facing 配額」— 處理範本級別。

### Case over-extrapolate spot-check

**0 / 8 處 over-extrapolate**。sample 中 case 引用都嚴謹標口徑：

- DraftKings 17K ops/sec 標「200 shard 加總、非單 DB」
- Microsoft 365 dogfood 數字不公開、被反覆明示「不能當 benchmark」
- Coinbase 60K / 2K「兩個獨立口徑（rate vs concurrent count）、不是同一數字連續變化」處理範本級
- Netflix +75% 標「workload 改善幅度 10-75% 不等、不是每個都 75%」
- Hard Rock「省 10-20 工程師」反覆強調「機會成本、非已 hire 後可裁員」

R4 polish 已修完 case fidelity、本輪 Round 5-C steelman 視角沒新增 over-extrapolate finding。

## Outbound impact 結果

新 article + 12 新 cards 完成、但既有 1.x / 9.x / 4.x / 6.x 章節幾乎沒反向 cross-link。重大斷裂。

### 既有 1.x 章節缺 link

11 篇 1.x 章節中 *9 篇* 完全沒 link 到本批 32 deep article（schema-design / schema-migration-rollout-evidence 各 1 link）：

- **1.5 transaction-boundary**：提 9.C10 Spanner external consistency / 9.C4 DraftKings / 9.C14 Standard Chartered case、但沒 link `spanner/truetime-api-depth`、`aurora/storage-architecture`、`cockroachdb/transaction-retry-pattern`。
- **1.10 kv-document-capacity-planning**：講 composite partition key / write sharding / on-demand vs provisioned / Cosmos DB synthetic key — 全是新 article 覆蓋的議題、但沒 link `dynamodb/partition-key-antipatterns` / `dynamodb/on-demand-vs-provisioned` / `cosmosdb/partition-key-design` / 新卡 `composite-partition-key`。**高 impact**。
- **1.11 global-distributed-oltp**：提 TrueTime / Aurora DSQL / CockroachDB / Cosmos DB consistency level — 全是本批 article 主議題、但只 link case、沒 link `spanner/truetime-api-depth`、`spanner/consistency-models-comparison`、`cockroachdb/aurora-dsql-spanner-decision-tree`、`cosmosdb/consistency-levels-engineering`。**最高 impact**。
- **1.6 high-concurrency-access**：connection pool 議題、應 link `mongodb/connection-management-and-cache-layer` 跟新卡 `freshness-token`。
- **1.12 large-scale-db-migration**：跨 vendor migration、應 link `cosmosdb/mongodb-api-vs-sql-api`、`aurora/migrate-from-self-managed-pg-mysql`、`spanner/migrate-from-cloud-sql-pg`。
- **1.7 state-ownership-query-boundary** / **1.4 repository-adapter** / **1.8 reconciliation-data-repair** / **1.9 red-team-data-layer** 視議題輕重補。

### 既有 9.x case 缺 routing

21 個相關 case 中只 6 個 link 到 vendor article（doordash / forbes / coinbase / hard-rock / netflix-cockroachdb / toyota）。其餘 15 個包含主要 anchor case 都沒在「下一步路由」加 deep article link：

- **9.C4 DraftKings Aurora financial ledger** → 應 link `aurora/storage-architecture`（DraftKings 6ms 寫 / <1ms 讀 / 雙峰錯位 / 200 cluster 都在 storage-architecture 主寫）、`aurora/read-replica-scaling`。**最高 impact**。
- **9.C23 Netflix Aurora consolidation** → 應 link `aurora/storage-architecture`（+75% root cause 主寫位）。
- **9.C14 Standard Chartered** → 應 link `aurora/cross-az-failover-rto` + `aurora/global-database-multi-region`（anti-recommendation 主寫位）+ `cockroachdb/aurora-dsql-spanner-decision-tree`。
- **9.C5 Amazon Ads / 9.C15 Tixcraft / 9.C24 Genesys** → 應 link `dynamodb/partition-key-antipatterns` 跟 `dynamodb/on-demand-vs-provisioned`。
- **9.C10 Spanner** → 應 link `spanner/truetime-api-depth` + `spanner/consistency-models-comparison`。
- **9.C11 Minecraft Earth / 9.C21 ASOS / 9.C30 Microsoft 365** → 應 link `cosmosdb/*` 對應深 article。
- **9.C36 Coinbase / 9.C37 Forbes / 9.C38 Toyota** 已有部分、但 Toyota 應補 `mongodb/shard-key-selection`、Coinbase 應補 `mongodb/connection-management-and-cache-layer`（最直接 anchor）。

### 既有 4.x / 6.x / 9.x 缺 link

跨層章節幾乎沒 link：

- **4.20 observability-evidence-package**：本批 article 大量 cross-link（Aurora storage / Spanner truetime / Cosmos DB capacity 都引用）、但 4.20 沒反向 link 到任何 vendor deep article。
- **9.4 saturation-discovery / 9.5 bottleneck-localization / 9.6 capacity-planning**：本批 article 大量 cross-link、但反向沒 link。
- **9.11 peak-event-readiness**：本批 `on-demand-vs-provisioned` Frame 8 五型 scaling 是直接覆蓋的議題、9.11 沒 link。
- **9.7 connection-pool-amplification**：已 link 到 `vendors/` index、但沒 link `mongodb/connection-management-and-cache-layer`（最直接 anchor）— 建議升級具體 link。
- **6.11 migration-safety**：本批 migration article（mongodb-api-vs-sql-api / migrate-from-self-managed-pg-mysql / migrate-from-cloud-sql-pg）沒反向 link。

### Knowledge card 缺口（重 audit）

12 新 cards 涵蓋 *High 7 + Medium ROI 高 5*、跟 audit 結論一致。重 audit 不建卡候選後沒發現判斷錯誤需要重新評估：

- `DAX` / `mongobetween` / `global-tables` / `synthetic-partition-key` / `outpost-deployment` / `dogfood-signal` — 仍合理不建卡（vendor-specific 細節 / 已被既有卡承擔 / 屬寫作紀律）。
- `aggregate-root` / `change-stream` / `resume-token` / `survival-goal` / `processing-unit` — Medium 中 5 張仍 backlog、不影響當前 32 篇 article 可讀性、可後續評估。
- **新發現缺口**：「PostgreSQL 相容性 audit checklist 4 項」（serializable default / retry semantics / partial index / 其他 SQL 行為）是 `aurora-dsql-spanner-decision-tree` + `transaction-retry-pattern` 反覆出現的 frame、屬本批合成 frame、不建卡（屬 article 內 frame 命名）— 結論一致。

## 必修 / 建議分類

### 必修（5 處）

1. **DraftKings case + Netflix Aurora case + Standard Chartered case 下一步路由補 Aurora deep article link** — 三個最強 anchor case 反向引用斷裂、讀者無法從 case 進深 article。
2. **1.10 kv-document-capacity-planning 補 dynamodb/cosmosdb deep article link** — 章節直接覆蓋本批 article 主議題、目前完全沒 link。
3. **1.11 global-distributed-oltp 補 spanner / cockroachdb / cosmosdb deep article link** — 同上。
4. **1.5 transaction-boundary 補 vendor link**（提 case 但漏 deep article link）。
5. **`aurora-dsql-spanner-decision-tree` 跟 `transaction-retry-pattern` 補通用估算 scope warning**（90% single-cloud / 2-5x latency / avg retry 0.3 / conflict 100% 等通用數字應明示「通用工程估算、case 未揭露」）。

### 建議（4 處）

1. **9.C5 Amazon Ads / 9.C15 Tixcraft / 9.C10 Spanner / 9.C11 Minecraft Earth / 9.C30 Microsoft 365 等 case 下一步路由補 vendor deep article link**。
2. **4.20 observability-evidence-package + 9.4/9.5/9.6 補 vendor deep article link**（跨層章節反向引用斷裂）。
3. **`transaction-retry-pattern` 失敗模式補「distributed deadlock × retry 互動」mode**（less obvious 但 production 偶見）。
4. **`mongodb-api-vs-sql-api` RU 10-20% overhead 數字補來源**（標 vendor docs vs 通用估算）。

### Top 3 high-impact 發現

1. **outbound reverse-link 全面斷裂**：21 case 中 15 個沒 routing link、11 個 1.x 章節 9 個沒 link — 讀者從 1.x 章節或 case 進不了本批 deep article、新內容對既有讀者旅程影響趨近於零。
2. **DraftKings / Netflix Aurora / Standard Chartered 三大 anchor case 完全沒反向 link** — 這三個 case 是本批 Aurora 5 篇 deep article 的最強 anchor、case 讀者該被導入 deep article 才符合「case → deep article」learning path。
3. **5 處未明示通用估算數字**：90% single-cloud / 2-5x latency / 6-7x rate / 10-20% RU overhead / 3-5ms cross-AZ — 應跟 truetime article 對齊範本、補 scope warning。
