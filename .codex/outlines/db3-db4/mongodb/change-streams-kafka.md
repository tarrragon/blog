# MongoDB Change Streams + Kafka 整合：resume token、scope 選擇與 connector 治理

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- Application 寫 MongoDB 後還要 dual-write Elasticsearch / Redis / data warehouse、application code 越塞越多 hook、寫入失敗的補償邏輯散落各處
- 改用 change stream → Kafka → downstream sink 後、有了第一版 CDC pipeline、但連續工作幾週後出現「downstream 漏 event」或「duplicate event」
- Connector restart 後 resume token 過期（oplog 已滾掉）、整個 collection 必須重灌
- Sharded cluster 上 collection-level change stream 跟 cluster-wide change stream 行為不同、application 連 mongos 跟連 single shard 拿到不同 event
- 讀者徵兆：MongoDB Kafka Connector log `ChangeStreamHistoryLost` 或 `ResumeTokenChanged`、downstream Kafka topic event count vs source collection write count 不平、replication oplog 跟 change stream consumer 的 lag 同時升
- Case anchor: needs new case（CDC pipeline resume token 過期導致全量重灌 incident）；側面引用 [Spotify Kafka → PubSub migration](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)（pipeline-level migration 經驗對照）

## 核心機制（Vendor-specific mechanism）

- Change stream 是 MongoDB 3.6+ 原生 CDC、本質上是 oplog tail 包裝成 cursor API；可以從 collection / database / cluster 三個 scope 開
- Oplog 是 capped collection、預設 size = disk 5% 或 50GB（取較小）；resume token 對應 oplog entry 的 timestamp + UUID + documentKey
- Resume token 有兩種：`_id`（每個 event 都帶）跟 `startAfter` / `resumeAfter` parameter；token 必須對應仍在 oplog 內的 entry，oplog 滾掉 → `ChangeStreamHistoryLost`
- `fullDocument: "updateLookup"`：update event 預設只給 delta、加這個 option 會額外 query 一次 primary 拿完整 doc；高頻 update 下成本顯著
- Pre-image / post-image（6.0+）：可以拿到 update 前的 doc 狀態、需 collection-level option `changeStreamPreAndPostImages`
- Cluster-wide vs collection-level change stream：sharded cluster 上 cluster-wide 必須打 mongos、event ordering 是 global；collection-level 可直接打單 shard、ordering 只在該 shard 內
- MongoDB Kafka Connector（Confluent / MongoDB 官方）：source connector 把 change stream → Kafka topic、sink connector 把 Kafka topic → MongoDB；at-least-once 語義、需 application 處理 idempotency
- 對應 knowledge card: [change-data-capture](/backend/knowledge-cards/change-data-capture/)、[replication-channel](/backend/knowledge-cards/replication-channel/)、[replication-slot](/backend/knowledge-cards/replication-slot/)（雖然 MongoDB 沒 slot、概念對照）

## 操作流程（Operations）

- Step 1：scope 決策樹 — 單 collection / 多 collection / 整 database / 整 cluster；scope 越大 connector 容易擴展但 event ordering / filtering 成本越高
- Step 2：oplog sizing — 容量公式 `oplog size >= peak write rate × max acceptable consumer downtime`；典型設 24-72 小時可恢復窗口
- Step 3：連 Kafka Connector：

  ```json
  {
    "connector.class": "com.mongodb.kafka.connect.MongoSourceConnector",
    "connection.uri": "mongodb://...",
    "database": "shop",
    "collection": "orders",
    "publish.full.document.only": "true",
    "change.stream.full.document": "updateLookup",
    "copy.existing": "true",
    "copy.existing.namespace.regex": "shop\\.orders",
    "errors.tolerance": "none",
    "offset.flush.interval.ms": "10000"
  }
  ```

- Step 4：resume token persistence — connector 把 token 寫 Kafka `__consumer_offsets` 或外部 store；application 自管 change stream 時要寫到 durable store
- Step 5：filter pipeline — change stream 支援 aggregation pipeline `[{$match: {...}}]`、把過濾下推到 MongoDB、減少 connector 處理量
- Step 6：downstream idempotency — sink 收 Kafka event 時用 `documentKey._id + clusterTime` 做 dedup key
- 驗證點：source collection write count vs Kafka topic event count 差異 < 0.1%、resume token age < oplog retention 的 50%、connector restart drill 能 5 分鐘內接回
- Rollback boundary：source connector 是 read-only 對 MongoDB 無傷；sink connector 要備份 target 才能還原；resume token 寫錯 → 從 `startAtOperationTime` 回退到時間點重跑

## 失敗模式（Failure modes）

- **Resume token 過期（oplog 滾掉）**：connector down 太久、oplog 已超出 retention、`ChangeStreamHistoryLost` → 必須 `copy.existing` 全量重灌、期間 downstream 看不到新資料
- **updateLookup 在高頻 update 下打爆 primary**：每筆 update event 都觸發一次 primary query、primary 負擔翻倍；改 collection-level pre/post image（6.0+）或在 application 補完整 doc
- **Sharded cluster cluster-wide stream 打爆 mongos**：所有 shard 的 event 都收斂到 mongos、mongos 變單點瓶頸；改 collection-level stream 多 connector 並行
- **At-least-once 變 duplicate flood**：connector restart 點之後幾分鐘 event 重發、downstream 沒做 idempotency → 重複 side effect（重複發 email、重複扣款）
- **Schema drift 突然 break sink**：MongoDB 寫了新欄位 / 改型別、sink connector 的 JSON schema 不認、batch 停在 dead-letter queue
- **Backup / DDL 期間 change stream 異常**：`reIndex` / `compact` / `dropCollection` 觸發特殊 event、connector 沒處理 → consumer 停
- Anti-recommendation：簡單的 outbox pattern + application transactional write 對於低吞吐 / 單 sink 的場景比 change stream + Kafka 簡單；不是所有「需要 event 通知」的場景都要 CDC pipeline；若 downstream 只是同一 region 同團隊的 Elasticsearch index、`$merge` 或 application 雙寫 + 對賬可能成本更低

## 容量與觀測（Capacity & observability）

- 關鍵 metric：oplog 寫入速率與保留時間、change stream cursor age、connector lag（Kafka offset 對比 source write）、resume token 距 oplog 頭尾的距離
- Mongo command：`db.getReplicationInfo()`（oplog 大小 / 時間範圍）、`db.printReplicationInfo()`、`db.currentOp({ "op": "getmore", "ns": "local.oplog.rs" })` 看 change stream consumer
- Connector metric：Kafka Connect JMX 的 `source-record-poll-rate`、`source-record-write-rate`、`offset-commit-success-rate`
- Downstream observability：event count diff（source write count vs sink apply count）、event time → arrival time lag 分布
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：oplog retention + connector lag + dedup rate 是 CDC pipeline 健康狀態 evidence 三件套
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：CDC lag 升高時區分 (a) source oplog 寫太快 (b) connector 處理慢 (c) downstream sink 慢

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[shard key selection](./shard-key-selection.md)（cluster-wide vs collection-level change stream 在 sharded cluster 的選擇）、[replica set read preference](./replica-set-read-preference.md)（change stream 對 primary load 的影響、能否走 secondary）、[schema design pattern](./schema-design-pattern.md)（schema validator 對下游 sink 的契約意義）
- Migration playbook：MongoDB → 其他 sink 的 bulk migration 走 [→ Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 用 Atlas Migration Service；遷出 MongoDB 時 change stream 是 catch-up 機制 [→ MongoDB → DynamoDB / Cosmos DB](/backend/01-database/vendors/mongodb/)
- 跟 1.x 互引：[1.6 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 處理 schema drift 時 CDC pipeline 的對賬；[1.7 reconciliation data repair](/backend/01-database/reconciliation-data-repair/) 處理 CDC 失準後的對賬流程

## 寫作前置 checklist

- [ ] Case anchor：resume token 過期導致全量重灌的具體 incident 強烈需要新建 case（含 oplog retention 設定、影響時間、修法）
- [ ] Knowledge card 雙引用：change-data-capture + replication-channel 都已存在
- [ ] Sibling 對比清楚：跟 PostgreSQL logical replication + Debezium、MySQL binlog + Debezium、DynamoDB Streams 對比；本文是 MongoDB-specific（change stream API + resume token + cluster-wide scope）
- [ ] 預估寫作長度：260-320 行（CDC pipeline 議題大、需要 connector config + 6 個 failure mode + idempotency 治理）
