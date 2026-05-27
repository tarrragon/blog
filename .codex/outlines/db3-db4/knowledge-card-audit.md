# DB3 / DB4 Knowledge Card Gap Audit

## Audit 範圍 + 既有 card 規模

- 32 檔 article（MongoDB 6 / DynamoDB 5 / Cosmos DB 5 / Aurora 5 / CockroachDB 5 / Spanner 4 / DB3 entry 1 / 12 個原本沒列入清單但實際存在的 vendor `_index.md` 跟 `migrate-to-atlas` / `shard-expansion-multi-dc` / `consistency-model-optimization` 不計入）
- 抽出約 110 個關鍵術語、語意責任各異
- 對照 351 個既有 knowledge cards（`content/backend/knowledge-cards/` 下 .md 計數）
- 約 38 個術語已 covered（含 `hot-partition` / `truetime` / `consistency-level` / `quorum` / `rto` / `rpo` / `replication-lag` / `predictive-scaling` / `change-data-capture` / `external-consistency` / `linearizability` / `stale-read` / `session-consistency` / `database-sharding` / `failover` / `replication-slot` / `partition` / `transaction-boundary` / `isolation-level` / `connection-pool` / `vendor-lock-in` / `distributed-sql` / `pacelc` / `cap` / `blast-radius` / `eventual-consistency` / `consensus-protocol` / `durable-queue` / `retry-storm` / `latency-budget` / `single-writer-model` / `peak-forecast` / `cost-per-request` 等）
- 約 72 個 gap candidates、其中 *純名詞型* gap 占多數、*情境型新議題* gap 較少
- **整體 ROI 評估偏保守**：多數 gap 是 vendor-specific 機制（reshardCollection / interleave / Outposts / DAX 等）— 屬 vendor 文件域、AGENTS.md §3「讀者缺此術語難理解教材」判準下、多數應 *不建卡*（已在 article 內定義即可），少數真正跨 case / 跨 vendor 重複出現的 atomic concept 才建卡

---

## High Priority Candidates（建議立即補、預期 8 張）

### Candidate 1: `freshness-token`

- **slug**：`freshness-token`
- **語意責任**：寫入後返回的版本 token、後續 read 帶 token、保證 read 看到的資料 ≥ token 版本；解 DB + cache *跨層* read-after-write 的協議
- **出現**：12+ 次 / 4 篇（MongoDB connection-management-and-cache-layer / MongoDB replica-set-read-preference / Cosmos DB consistency-levels-engineering 對照、DB3 entry federated frame 提到）
- **跟既有 cards 關係**：
  - 跟 [session-consistency](/backend/knowledge-cards/session-consistency/) 區分（後者是 DB 內 causal、freshness-token 是跨層協議）
  - 跟 [stale-read](/backend/knowledge-cards/stale-read/) 區分（前者是症狀、freshness-token 是防護機制）
  - 跟 [cache-invalidation](/backend/knowledge-cards/cache-invalidation/) 互補（後者是 write 端、freshness-token 是 read 端契約）
- **建卡判準**：AGENTS.md §3「名詞跨情境變義、必拆卡、不可混寫」— freshness-token 跟 session token 在 MongoDB / Cosmos DB 各自命名不同（前者是 Coinbase 自建協議、後者是 Cosmos DB SDK 內建）、但語意責任相同；建一張 atomic 卡承擔「DB + cache 跨層版本協議」這個語意。讀者進大規模 OLTP 三層架構（driver + cache + scaling）章節必看
- **參考引用**：
  - MongoDB connection-management-and-cache-layer L62-75（freshness token 機制四步、跟 causal session 區分）
  - MongoDB replica-set-read-preference L68-83（DB 層 vs cache 層機制對照三選一表）
  - Cosmos DB consistency-levels-engineering session token 管理段（跨 service 傳遞）
- **優先序**：High

### Candidate 2: `leaseholder`

- **slug**：`leaseholder`
- **語意責任**：分散式 SQL（CockroachDB / Spanner）每個 range 在任一時間點的 read / write entry point、通常等於 Raft leader、承擔該 range 的 coordination；leaseholder 集中即是 hot range 根因之一
- **出現**：15+ 次 / 4 篇（CockroachDB hlc-raft-consensus / survival-goals / locality-aware-schema / aurora-dsql-spanner-decision-tree）
- **跟既有 cards 關係**：
  - 跟 [consensus-protocol](/backend/knowledge-cards/consensus-protocol/) 互補（後者是抽象機制、leaseholder 是 distributed SQL 內 per-range 落地）
  - 跟 [hot-partition](/backend/knowledge-cards/hot-partition/) 對照（KV 是 partition hot、distributed SQL 是 leaseholder hot、機制不同責任相近）
  - 跟 [single-writer-model](/backend/knowledge-cards/single-writer-model/) 區分（後者是 cluster-level、leaseholder 是 range-level）
- **建卡判準**：AGENTS.md §3「讀者若缺少某術語難以理解教材」— distributed SQL deep article 大量使用 leaseholder 概念解釋 latency / hot range / lease transfer p99 spike、不建卡讀者要每篇看 CockroachDB / Spanner 都重新定義
- **參考引用**：
  - CockroachDB hlc-raft-consensus L92-101（leaseholder 概念 + lease transfer）
  - CockroachDB locality-aware-schema L73-83（leaseholder 跟 voting / non-voting replica）
  - aurora-dsql-spanner-decision-tree（cluster boundary 段、leaseholder 分布判讀）
- **優先序**：High

### Candidate 3: `range` (range partitioning / range-based sharding)

- **slug**：`range-sharding`（建議用此 slug 避免跟既有 `partition` 卡衝突）
- **語意責任**：分散式 SQL（CockroachDB / Spanner）把 key space 切成可自動 split / merge 的 range（典型 ~512MB CockroachDB / Spanner split）、每個 range 自己的 consensus group、application 透明
- **出現**：20+ 次 / 5 篇（CockroachDB 全 5 篇 + Spanner truetime / schema-migration）
- **跟既有 cards 關係**：
  - 跟 [partition](/backend/knowledge-cards/partition/) 區分（後者是 Kafka / KV 風格的 hash / explicit partition、range 是 distributed SQL 透明 range-based）
  - 跟 [database-sharding](/backend/knowledge-cards/database-sharding/) 區分（後者是 application-level sharding、range 是系統內 transparent）
  - 跟 [table-partitioning](/backend/knowledge-cards/table-partitioning/) 區分（後者是 PostgreSQL declarative partition、range 是 distributed SQL 範疇）
- **建卡判準**：AGENTS.md §3「名詞跨情境變義」— 「partition」在 KV / Kafka / 分散式 SQL 是不同語意、需要 atomic 卡承擔「distributed SQL 透明 range-based partitioning」這個獨立語意；讀者不識別 range 跟 partition 差異會把 KV hot partition 解法套到 hot range、誤判
- **參考引用**：
  - CockroachDB hlc-raft-consensus L80-90（range 概念 + 跟其他 vendor 對照）
  - Spanner schema-migration-interleaved-tables L66-77（interleaved + split-by-range）
- **優先序**：High

### Candidate 4: `hlc` (hybrid logical clock)

- **slug**：`hybrid-logical-clock`
- **語意責任**：用 physical wall clock + monotonic logical counter 給每個事件 timestamp、不依賴硬體原子鐘、靠軟體 max-offset 保證跨節點時鐘差不超過上限（典型 500ms）、超過就 panic 保護一致性
- **出現**：8+ 次 / 3 篇（CockroachDB hlc-raft-consensus / survival-goals / aurora-dsql-spanner-decision-tree）
- **跟既有 cards 關係**：
  - 跟 [truetime](/backend/knowledge-cards/truetime/) 對照（兩者解同一 event ordering 問題、HLC 用軟體、TrueTime 用 GPS+原子鐘）
  - 跟 [external-consistency](/backend/knowledge-cards/external-consistency/) 互補（HLC 不保證 external consistency、只保證 linearizability）
- **建卡判準**：AGENTS.md §3「教學需求」— CockroachDB 路徑讀者必懂 HLC 跟 TrueTime 差異才能判讀「為何 CockroachDB 不付 commit wait」「為何 NTP 是 ops first-class concern」；既有只有 truetime 卡、缺 HLC 對照卡形成不對稱
- **參考引用**：
  - CockroachDB hlc-raft-consensus L35-58（HLC 機制 + 跟 TrueTime 對照表）
  - CockroachDB survival-goals L92-97（max-offset 配置紀律）
- **優先序**：High

### Candidate 5: `commit-wait`

- **slug**：`commit-wait`
- **語意責任**：Spanner external consistency 的核心機制 — read-write transaction 拿 commit timestamp s 後等待直到 `TT.after(s)` 才 ACK、wait 時間 ≈ 2ε、付這個 latency tax 換 transaction commit timestamp 順序 = real-time 順序
- **出現**：8+ 次 / 3 篇（Spanner truetime-api-depth / consistency-models-comparison / migrate-from-cloud-sql-pg）
- **跟既有 cards 關係**：
  - 跟 [truetime](/backend/knowledge-cards/truetime/) 緊密相關但獨立（前者是時鐘 API、commit-wait 是用它撐 external consistency 的具體機制）
  - 跟 [external-consistency](/backend/knowledge-cards/external-consistency/) 互補（commit-wait 是 *為什麼能* external consistency 的實作）
  - 跟 [latency-budget](/backend/knowledge-cards/latency-budget/) 互補（commit-wait 是無法 scale away 的固定 latency 支出）
- **建卡判準**：AGENTS.md §3「讀者缺此術語難理解教材」— Spanner sizing / capacity planning 章節大量用 commit-wait 概念解釋 write latency 拆解；不建卡讀者每次看 Spanner 章節都要重讀機制段
- **參考引用**：
  - Spanner truetime-api-depth L43-62（commit-wait 數學圖示 + ε 推導）
  - Spanner consistency-models-comparison L77-86（cross-region latency 拆解、commit-wait 是其中 2-14ms）
- **優先序**：High

### Candidate 6: `request-unit` / `ru`

- **slug**：`request-unit`
- **語意責任**：Cosmos DB 的容量抽象單位 — 1 RU = 1KB document strong-consistent read 的 CPU + memory + IOPS 綜合 cost、寫 ~5 RU、複雜 query 數百 RU；把容量規劃從「估 CPU / IOPS」變成「估每個操作多少 RU × 操作頻率」
- **出現**：30+ 次 / 5 篇（Cosmos DB ru-cost-model-sizing 全篇 + partition-key-design / consistency-levels-engineering / multi-region-write-conflict / mongodb-api-vs-sql-api）+ DB3 entry 對比表
- **跟既有 cards 關係**：
  - 跟 [cost-per-request](/backend/knowledge-cards/cost-per-request/) 互補（後者是抽象、RU 是 Cosmos DB 具體實作）
  - 跟 [throughput](/backend/knowledge-cards/throughput/) 區分（後者是 raw 計量、RU 是 vendor 抽象）
  - 跟 [workload-model](/backend/knowledge-cards/workload-model/) 互補
- **建卡判準**：AGENTS.md §3「教學需求」— Cosmos DB 整個 selection / sizing / cost 評估都圍繞 RU 思維、跟其他 vendor 的 capacity 抽象（CPU+IOPS、WCU/RCU、processing unit）不同；建卡可讓「思維遷移成本」議題有 atomic 引用點
- **參考引用**：
  - Cosmos DB ru-cost-model-sizing L29-49（從 CPU+IOPS 思維轉到 RU 思維 + 跨 vendor capacity 抽象對照）
  - Cosmos DB mongodb-api-vs-sql-api L143-160（API kind 對 RU consumption 影響）
  - DB3 entry vendor 對比 10 軸表（軸 4 capacity 抽象）
- **優先序**：High

### Candidate 7: `bounded-staleness`（**已存在、見下方拆卡候選段、考量是否補強**）

> 既有 `bounded-staleness` 卡存在於 351 個 cards 內、語意是「容忍 K 個 version / T 秒」的 staleness bound。Cosmos DB 5 level 之一、跟 Spanner read-only transaction 的 `bounded_staleness` API 對照。
>
> 此 candidate 從 High 移除、補強現有卡片即可、不新建。

### Candidate 8: `follower-read`

- **slug**：`follower-read`
- **語意責任**：分散式 SQL 從 non-voting replica 讀 closed timestamp 之前的資料、不參與 Raft commit、低 latency 但 read-after-write 場景仍可能 stale；用 follower-read 換 cross-region read latency 是常見策略
- **出現**：6+ 次 / 3 篇（CockroachDB locality-aware-schema / survival-goals / aurora-dsql-spanner-decision-tree）+ Spanner truetime-api-depth bounded staleness 對照
- **跟既有 cards 關係**：
  - 跟 [stale-read](/backend/knowledge-cards/stale-read/) 互補（後者是現象、follower-read 是有意選擇）
  - 跟 [fallback-read](/backend/knowledge-cards/fallback-read/) 區分（後者是 failure 時的降級、follower-read 是常態低 latency 路徑）
  - 跟 [read-write-split](/backend/knowledge-cards/read-write-split/) 區分（後者是 application-level、follower-read 是 distributed SQL 內機制）
- **建卡判準**：AGENTS.md §3「讀者若缺少某術語難以理解教材」— distributed SQL 跨 region 設計章節大量使用 follower-read 概念解釋 latency 取捨；既有 stale-read 卡承擔 *現象*、缺 *機制名稱* 對應卡
- **參考引用**：
  - CockroachDB locality-aware-schema L77-83（voting vs non-voting replica + follower read）
  - CockroachDB survival-goals L49-53（voting / non-voting replica 機制）
  - Spanner truetime-api-depth L80-87（bounded staleness 三 SDK 選項）
- **優先序**：High

---

## Medium Priority Candidates（預期 10 張）

### Candidate M1: `serialization-failure` / `40001-error`

- **slug**：`serialization-failure`
- **語意責任**：SERIALIZABLE isolation 偵測到衝突、後到 transaction 被 abort 並回 SQL state `40001`、application 必須包 retry loop；CockroachDB / Spanner / PostgreSQL SSI 共通
- **出現**：8+ 次 / 1 篇主寫（CockroachDB transaction-retry-pattern）+ 2 篇 cross-link
- **跟既有 cards 關係**：跟 [isolation-level](/backend/knowledge-cards/isolation-level/) / [retry-storm](/backend/knowledge-cards/retry-storm/) / [transaction-boundary](/backend/knowledge-cards/transaction-boundary/) 共軸
- **建卡判準**：AGENTS.md §3「跨 vendor 共通名詞」— 不只 CockroachDB、Spanner / PG SSI / Aurora DSQL 都會觸發、建一張中性卡承擔「serializable 衝突 abort 協議」
- **參考引用**：CockroachDB transaction-retry-pattern L60-78（機制 + SAVEPOINT 範例）
- **優先序**：Medium

### Candidate M2: `composite-key` / `write-sharding-suffix`

- **slug**：`composite-partition-key`
- **語意責任**：用多欄位合成 partition key（如 `event_id#shard_id` / `tenant_id + user_id_hash`）、把單一 logical hot key 拆成 N 個物理 shard、寫入分散但讀路徑需要 fan-out
- **出現**：12+ 次 / 4 篇（DynamoDB partition-key-antipatterns / single-table-design-pattern / Cosmos DB partition-key-design / MongoDB shard-key-selection）
- **跟既有 cards 關係**：跟 [hot-partition](/backend/knowledge-cards/hot-partition/) / [database-sharding](/backend/knowledge-cards/database-sharding/) 是補位關係（前者是症狀、composite-key 是治療）
- **建卡判準**：AGENTS.md §3「跨 vendor frame 反覆出現」— DynamoDB / Cosmos DB / MongoDB 三家都用、cross-link 多
- **參考引用**：DynamoDB partition-key-antipatterns L74-113（random shard / calculated shard 兩種）、Cosmos DB partition-key-design L144-162（synthetic + fanout trade-off）
- **優先序**：Medium

### Candidate M3: `interleaved-table`

- **slug**：`interleaved-table`
- **語意責任**：Spanner 把 parent / child table row 在 storage layer 物理交錯儲存、不是純 logical foreign key、JOIN cost 接近 single-table access、`ON DELETE CASCADE` 是 storage-level
- **出現**：8+ 次 / 2 篇（Spanner schema-migration-interleaved-tables 全篇 + migrate-from-cloud-sql-pg phase 1 必讀）+ CockroachDB locality-aware-schema 對照
- **跟既有 cards 關係**：跟 [table-partitioning](/backend/knowledge-cards/table-partitioning/) / [transaction-boundary](/backend/knowledge-cards/transaction-boundary/) 鄰近
- **建卡判準**：Spanner-specific 但有 CockroachDB `REGIONAL BY ROW` 跟 parent-child co-location 對照、可以建中性卡承擔「parent-child physical co-location」這個概念
- **參考引用**：Spanner schema-migration-interleaved-tables L60-90（interleaved 機制 + 硬限）
- **優先序**：Medium

### Candidate M4: `survival-goal`

- **slug**：`survival-goal`
- **語意責任**：CockroachDB 的宣告式 HA 配置 — `SURVIVE ZONE FAILURE` / `SURVIVE REGION FAILURE`、決定 Raft replica 分佈規則、直接決定 RTO / RPO；對應業務「不能丟事件」清單
- **出現**：6+ 次 / 2 篇（CockroachDB survival-goals 全篇 + aurora-dsql-spanner-decision-tree）
- **跟既有 cards 關係**：跟 [rto](/backend/knowledge-cards/rto/) / [rpo](/backend/knowledge-cards/rpo/) / [quorum](/backend/knowledge-cards/quorum/) / [blast-radius](/backend/knowledge-cards/blast-radius/) 鄰近
- **建卡判準**：CockroachDB-specific 但概念可中性化為「宣告式 fault domain 配置」、其他 vendor（Aurora DSQL / Spanner）也有類似抽象
- **參考引用**：CockroachDB survival-goals L42-67（兩種 survival goal 機制 + 業務 SLO 倒推）
- **優先序**：Medium

### Candidate M5: `processing-unit` / `pu`

- **slug**：`processing-unit`
- **語意責任**：Spanner 的容量單位、100 pu ≈ 1 node（早期 minimum）；2021+ 推出 granular sizing 可從小、但 100 pu 起跳 cost 對中小 PG workload 仍是 sizing barrier
- **出現**：8+ 次 / 3 篇（Spanner truetime-api-depth / migrate-from-cloud-sql-pg / aurora-dsql-spanner-decision-tree）
- **跟既有 cards 關係**：跟 [cost-per-request](/backend/knowledge-cards/cost-per-request/) / [throughput](/backend/knowledge-cards/throughput/) 互補
- **建卡判準**：Spanner-specific 但 sizing barrier 議題反覆出現、建一張卡承擔「vendor 強制最小 footprint cost」這個 selection 議題
- **參考引用**：aurora-dsql-spanner-decision-tree L147-156（sizing barrier 段）
- **優先序**：Medium

### Candidate M6: `aggregate-root` / `aggregate-boundary`

- **slug**：`aggregate-root`
- **語意責任**：DDD 概念落地到 document model — 把「一起讀、一起寫、一致性邊界一致」的資料塞同一 document；MongoDB 寫入 atomicity 限制在單 document 內、跨 document 要 multi-document transaction（有性能成本）
- **出現**：8+ 次 / 2 篇（MongoDB schema-design-pattern 主寫 + DB3 entry workload shape 軸 1）
- **跟既有 cards 關係**：跟 [transaction-boundary](/backend/knowledge-cards/transaction-boundary/) 互補（aggregate-root 是 document 層、transaction-boundary 是更通用）、跟 [document-store](/backend/knowledge-cards/document-store/) 鄰近
- **建卡判準**：AGENTS.md §3「教學需求」— document model 章節無法跳過 aggregate root 概念、cross-link 點密
- **參考引用**：MongoDB schema-design-pattern L33-39（aggregate root 決定 atomicity 邊界）
- **優先序**：Medium

### Candidate M7: `change-stream` / `change-feed`

- **slug**：`change-stream`（建議卡涵蓋 MongoDB change stream + Cosmos DB Change Feed 共通機制）
- **語意責任**：document DB 的 CDC 介面、本質是 oplog tail 包裝、cursor-based 串流；resume token 對應 oplog entry 位置、token 過期意味 backfill
- **出現**：15+ 次 / 3 篇（MongoDB change-streams-kafka 全篇 + Cosmos DB mongodb-api-vs-sql-api / multi-region-write-conflict）
- **跟既有 cards 關係**：跟 [change-data-capture](/backend/knowledge-cards/change-data-capture/) 是補位關係（CDC 是抽象、change-stream 是 document DB 具體機制）、跟 [replication-slot](/backend/knowledge-cards/replication-slot/) 對照
- **建卡判準**：AGENTS.md §3「跨 vendor 共通機制」— 建一張 atomic 卡承擔「document DB CDC cursor」這個語意、避免讀者把 CDC / change-stream / replication-slot 混為一談
- **參考引用**：MongoDB change-streams-kafka L33-62（機制段 + scope 三選一）
- **優先序**：Medium

### Candidate M8: `resume-token`

- **slug**：`resume-token`
- **語意責任**：CDC pipeline 用來在中斷後續傳的位置標記、對應 oplog entry timestamp + UUID；token 過期（oplog 已滾掉）必須全量 backfill；MongoDB change stream / Cosmos DB Change Feed / Spanner change stream 都用類似概念
- **出現**：12+ 次 / 1 篇主寫（MongoDB change-streams-kafka）+ 2 篇 cross-link
- **跟既有 cards 關係**：跟 [change-data-capture](/backend/knowledge-cards/change-data-capture/) / [offset](/backend/knowledge-cards/offset/) / [replication-slot](/backend/knowledge-cards/replication-slot/) 鄰近但語意不同
- **建卡判準**：AGENTS.md §3「concept 跨 vendor 同名不同實作」— resume token 在 MongoDB / Cosmos DB / Aurora DSQL change stream / Spanner 各有具體 format、建中性卡承擔「CDC continuation token」概念
- **參考引用**：MongoDB change-streams-kafka L42-49 + L122-127（token 兩種用法 + 過期防護）
- **優先序**：Medium

### Candidate M9: `data-residency`

- **slug**：`data-residency`
- **語意責任**：合規要求資料留在特定地理邊界內、跨境複製違反合規；Aurora Global Database 在受監管金融場景反指標、CockroachDB locality + placement / DynamoDB region-pinned Global Tables 是合規吸收層
- **出現**：12+ 次 / 5 篇（Aurora global-database-multi-region / migrate-from-self-managed-pg-mysql / read-replica-scaling fleet 治理 / CockroachDB locality-aware-schema / DynamoDB global-tables-conflict）
- **跟既有 cards 關係**：跟 [tenant-boundary](/backend/knowledge-cards/tenant-boundary/) / [trust-boundary](/backend/knowledge-cards/trust-boundary/) 鄰近但語意明確分離（前者是合規 *地理* 邊界）
- **建卡判準**：AGENTS.md §3「跨 vendor frame 反覆出現」— 5 篇 article 用同一概念解釋「合規 driver 推 fleet 拓樸」、建中性卡承擔「資料駐留合規邊界」
- **參考引用**：Aurora migrate-from-self-managed-pg-mysql L48-54（no-go condition）、CockroachDB locality-aware-schema L162-180（Wire Act 對比 GDPR / PIPL / LGPD）
- **優先序**：Medium

### Candidate M10: `cross-region-quorum`

- **slug**：`cross-region-quorum`
- **語意責任**：multi-region distributed SQL（Spanner / CockroachDB region survival）強制 voting replica 跨 region、write commit 必須等多 region quorum ack、跨洲 RTT 物理硬限 100-200ms、是 line-rate scaling 的固定 latency 支出
- **出現**：10+ 次 / 4 篇（Spanner truetime-api-depth / consistency-models-comparison / CockroachDB survival-goals / aurora-dsql-spanner-decision-tree）
- **跟既有 cards 關係**：跟 [quorum](/backend/knowledge-cards/quorum/) 互補（後者是抽象、cross-region-quorum 是 distributed SQL 特定情境）、跟 [latency-budget](/backend/knowledge-cards/latency-budget/) 鄰近
- **建卡判準**：跨 vendor 共通的「物理光速下界 latency tax」frame、建卡可承擔這個跨章節反覆出現的判讀
- **參考引用**：Spanner consistency-models-comparison L77-97（cross-region quorum 100-200ms 物理硬限 + latency 拆解）
- **優先序**：Medium

---

## Low Priority Candidates（偶現一次、屬 vendor-specific 細節、預期 7 張、多數建議不建卡）

### Candidate L1: `dax`（DynamoDB Accelerator）

- **slug**：`dax`
- **語意責任**：DynamoDB 的 sub-region cache layer、讀峰值持續高時的補位、不是 GSI / LSI 同層方案
- **出現**：4 次 / 1 篇（DynamoDB gsi-lsi-design）
- **建卡判準**：vendor-specific、出現次數低、AGENTS.md §3 判準下傾向不建卡（讀者讀該 article 即可理解）
- **優先序**：Low — *不建議建卡*

### Candidate L2: `mongobetween` / `connection-proxy`

- **slug**：`connection-proxy`（建議中性命名涵蓋 mongobetween / pgbouncer / RDS Proxy）
- **語意責任**：把多 application process 連線多工成少量 DB 連線、解 process-per-core 部署模型的 connection storm
- **出現**：8 次 / 1 篇主寫（MongoDB connection-management-and-cache-layer）+ DB3 entry / Aurora cross-AZ failover 對照
- **跟既有 cards 關係**：跟既有 [connection-pool](/backend/knowledge-cards/connection-pool/) / [connection-pooler](/backend/knowledge-cards/connection-pooler/) 重疊
- **建卡判準**：concept 已被 `connection-pooler` 卡承擔、不需新建；補強既有卡更合理
- **優先序**：Low — *不建議建卡、補強既有 connection-pooler 卡*

### Candidate L3: `lww` (last-writer-wins)

- **slug**：`last-writer-wins`
- **語意責任**：multi-region active-active 的 conflict resolution 預設策略 — 用 timestamp 較大的 write 勝、clock skew 是隱性風險
- **出現**：10+ 次 / 3 篇（DynamoDB global-tables-conflict / Cosmos DB multi-region-write-conflict / CockroachDB 反例對照）
- **跟既有 cards 關係**：跟 [conflict-resolution](/backend/knowledge-cards/conflict-resolution/) 重疊（後者已存在）
- **建卡判準**：concept 已被 `conflict-resolution` 卡承擔；補強既有卡涵蓋 LWW / custom merge / conflict feed 三型即可
- **優先序**：Low — *不建議建卡、補強既有 conflict-resolution 卡*

### Candidate L4: `global-tables`（DynamoDB）

- **slug**：`global-tables` 或更中性 `multi-region-replication-group`
- **語意責任**：DynamoDB 的 multi-region active-active 機制、LWW conflict resolution、async replication、按 region 開關 replication
- **出現**：8 次 / 2 篇（DynamoDB global-tables-conflict 主寫 + DB3 entry 對比表）
- **建卡判準**：vendor-specific、屬 vendor 機制細節、AGENTS.md §3 判準下不建卡
- **優先序**：Low — *不建議建卡*

### Candidate L5: `synthetic-partition-key`

- **slug**：`synthetic-partition-key`
- **語意責任**：用 `userId_random` 把單一 user 寫入散到 N 個 partition、avoid hot logical partition；read 端需要 fan-out
- **出現**：5 次 / 1 篇（Cosmos DB partition-key-design）
- **建卡判準**：跟 Candidate M2 `composite-partition-key` 概念重疊、合併到 composite-key 卡即可
- **優先序**：Low — *不建議建卡、合併到 composite-partition-key*

### Candidate L6: `outpost-deployment`

- **slug**：`edge-compute-deployment`（中性命名涵蓋 AWS Outposts / Azure Stack）
- **語意責任**：把雲服務硬體部署到合規邊界內（如美國 sportsbook Wire Act 跨州合規要求運算留州內）
- **出現**：5 次 / 1 篇（CockroachDB locality-aware-schema）
- **建卡判準**：屬合規 + 部署架構 niche、不適合 atomic card、留在 article 內處理即可
- **優先序**：Low — *不建議建卡*

### Candidate L7: `dogfood-signal`

- **slug**：`dogfood-signal`
- **語意責任**：雲商旗艦 DB 用在自家旗艦產品上（Spanner @ Google Ads、DynamoDB @ Amazon Prime Day、Cosmos DB @ Microsoft 365）— selection signal 權重高、但 *不是* production benchmark 數字
- **出現**：8 次 / 3 篇（Cosmos DB mongodb-api-vs-sql-api / Spanner truetime-api-depth / aurora-dsql-spanner-decision-tree）+ DB3 entry
- **建卡判準**：屬寫作 / 引用紀律議題、不是工程概念、AGENTS.md §3「概念索引」判準下不建卡；應放 article 內或 outline knowledge
- **優先序**：Low — *不建議建卡*

---

## 拆卡候選（既有 cards 跨情境變義、預期 2 張）

### 拆卡 1: `partition` 跨情境變義

- **既有 card**：[partition](/backend/knowledge-cards/partition/) — 預設 Kafka / 事件流 partition 語意
- **變義跡象**：
  - DynamoDB / Cosmos DB partition 是 KV 自動 split 的物理單位、語意是「容量上限的物理 unit」
  - CockroachDB / Spanner range 是 distributed SQL 的 range-based partitioning、語意是「key space 透明切分」
  - Kafka / 訊息系統 partition 是事件流的有序切片、語意是「並行處理 + ordering 邊界」
- **建議**：保留 `partition` 為事件流定義（既有）、新建 `range-sharding`（見 High Candidate 3）承擔 distributed SQL 語意；KV partition 已被 `hot-partition` 跟 `database-sharding` 從不同角度承擔、不必另拆
- **優先序**：Medium（跟 High Candidate 3 同議題）

### 拆卡 2: `consistency-level` vs `external-consistency` vs `linearizability` 三者邊界

- **既有 cards**：[consistency-level](/backend/knowledge-cards/consistency-level/) / [external-consistency](/backend/knowledge-cards/external-consistency/) / [linearizability](/backend/knowledge-cards/linearizability/)
- **變義跡象**：Spanner consistency-models-comparison 揭露三者常被混用、Cosmos DB 5 level / Spanner external consistency / DynamoDB strong / PG SSI 在不同光譜上、讀者選型常因混淆做錯決策
- **建議**：**不新拆卡、補強既有 3 張卡的 cross-link 跟邊界段** — 在 consistency-level 卡內加入「跟 external-consistency / linearizability 的精確差異」段、補對應路由連結
- **優先序**：Medium — 動既有卡的維護議題、不是新建卡

---

## 不建卡候選（明確排除、避免 card 庫膨脹）

下列術語在 32 篇 article 中出現但 *不建議建卡*、理由分類：

| 術語                                 | 不建卡理由                                                   |
| ------------------------------------ | ------------------------------------------------------------ |
| `reshardCollection` (MongoDB 4.4+)   | vendor-specific 工具語法、屬 vendor 文件域                   |
| `$lookup` / `$merge` (MongoDB)       | SQL-equivalent 操作、屬 query syntax、不適合 atomic card     |
| `$jsonSchema` validator              | vendor-specific config syntax                                |
| `oplog`                              | vendor-specific WAL 名稱、概念已被 `write-ahead-log` 承擔    |
| `WCU` / `RCU` (DynamoDB)             | vendor-specific 計量單位、跟 RU 同類但 vendor 文件已充分定義 |
| `GSI` / `LSI`                        | vendor-specific 機制名稱、屬 DynamoDB 文件域                 |
| `gateway_region()` (CockroachDB)     | vendor-specific function 名稱                                |
| `crdb_region` (CockroachDB)          | vendor-specific 隱含欄位                                     |
| `PENDING_COMMIT_TIMESTAMP` (Spanner) | vendor-specific sentinel                                     |
| `aurora-iopt1` / Aurora storage tier | vendor-specific 配置選項                                     |
| `mongobetween` 具體名稱              | 概念已歸 `connection-proxy` / `connection-pooler`            |
| 「fleet of clusters」                | 屬 frame 名稱、article 內定義即可、不是 atomic concept       |
| 「artery of small databases」        | 屬 case-specific 修辭、不適合 atomic card                    |
| 「contract layer」                   | 屬 article 內 frame 命名、不是跨情境通用名詞                 |
| 「dogfood signal」                   | 屬寫作紀律議題、不是工程概念                                 |
| 「scope warning」                    | 屬寫作紀律、不是工程概念                                     |
| 「driver path」                      | 屬本 vendor 系列敘事 frame                                   |
| 「fact vs derive 分層」              | 屬寫作方法論                                                 |

---

## 跨章節 cross-link 建議（補強既有 cards 在 31 篇 article 沒被 link 到）

下列既有 cards 跟 DB3 / DB4 article 高度相關、但 article 沒 link 到、建議補 cross-link：

- **[external-consistency](/backend/knowledge-cards/external-consistency/)**：Spanner / CockroachDB / Aurora DSQL 比較相關文章都應 link、目前主要在 truetime / consistency-models-comparison 提到、aurora-dsql-spanner-decision-tree 應加
- **[pacelc](/backend/knowledge-cards/pacelc/)**：Cosmos DB consistency 文章用 PACELC frame 但沒 link 卡片、應補
- **[cap](/backend/knowledge-cards/cap/)**：Cosmos DB multi-region-write-conflict 開頭 AP 取捨段應 link、目前沒 link
- **[blast-radius](/backend/knowledge-cards/blast-radius/)**：MongoDB shard-key-selection（單 cluster vs 多 cluster）/ Aurora fleet 治理 / CockroachDB cluster boundary 都用、目前 link 不一致
- **[vendor-lock-in](/backend/knowledge-cards/vendor-lock-in/)**：Cosmos DB mongodb-api-vs-sql-api Framing 4 / Aurora migration no-go condition / aurora-dsql-spanner-decision-tree 都用、目前 link 不一致
- **[peak-forecast](/backend/knowledge-cards/peak-forecast/)**：DynamoDB on-demand-vs-provisioned / Cosmos DB ru-cost-model-sizing 都用、應 link
- **[scheduled-scaling](/backend/knowledge-cards/scheduled-scaling/)**：Cosmos DB ru-cost-model-sizing / DynamoDB on-demand-vs-provisioned / Aurora read-replica-scaling 都用、應 link
- **[idempotency](/backend/knowledge-cards/idempotency/)**：CockroachDB transaction-retry-pattern 反覆強調、應 link、目前沒 link
- **[saga](/backend/knowledge-cards/saga/)**：DynamoDB global-tables-conflict 跨 region transaction 失敗段提到 saga、應 link
- **[outbox-pattern](/backend/knowledge-cards/outbox-pattern/)**：MongoDB change-streams-kafka anti-recommendation 段提到 outbox 對照、應 link
- **[migration](/backend/knowledge-cards/migration/)** + **[migration-gate](/backend/knowledge-cards/migration-gate/)**：所有 migrate-* article 都應 link

---

## 統計摘要

| 項目                         | 數量                                     |
| ---------------------------- | ---------------------------------------- |
| Total 抽出術語               | ~110                                     |
| 已 covered（既有 351 cards） | ~38                                      |
| **High priority gap**        | **7**（去除 1 既有的 bounded-staleness） |
| **Medium priority gap**      | **10**                                   |
| **Low priority gap**         | **7**                                    |
| **拆卡候選**                 | **2**（保守、補強既有 card 為主）        |
| **明確不建卡**               | **~17 個術語**                           |
| **建議補 cross-link 既有卡** | **11 張**                                |

**ROI 評估**：

- 真正值得建的卡集中在 High priority 7 張（freshness-token / leaseholder / range-sharding / hybrid-logical-clock / commit-wait / request-unit / follower-read）
- Medium 10 張可分階段加（先 serialization-failure / composite-partition-key / interleaved-table / data-residency / cross-region-quorum 這 5 張 ROI 最高、後 5 張可後續評估）
- Low priority 7 張多數建議 *不建卡*、補強既有卡或留在 article 內處理
- 預估工時：High 7 張 ~3-4 小時、Medium 5 張優先批 ~2 小時、cross-link 補強 ~1 小時 — 合計 6-7 小時可完成主要建卡 + cross-link

**整體建議**：

- 立即補：High priority 7 張新卡 + 11 張既有卡的 cross-link 補強
- 排程補：Medium priority 5 張 ROI 較高的新卡
- 保守處理：拆卡只動既有 partition 卡並新建 range-sharding（已在 High 內）、其他既有卡用補段方式而非拆卡
- 不補：Low priority 大多數 + 明確排除清單上的所有術語
