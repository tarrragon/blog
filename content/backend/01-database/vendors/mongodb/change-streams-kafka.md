---
title: "MongoDB Change Streams + Kafka 整合：resume token、scope 選擇與 connector 治理"
date: 2026-05-27
description: "MongoDB change streams 機制（resume token、oplog 容量、cluster-wide vs collection-level scope）跟 Kafka Connector 整合；at-least-once 語義 + idempotency 治理 + resume token 過期防護"
weight: 35
tags: ["backend", "database", "mongodb", "change-streams", "cdc", "kafka", "deep-article"]
---

MongoDB change streams 是 3.6+ 原生 CDC 介面、本質上是 oplog tail 包裝成 cursor API。Application 從 dual-write 模式（自己寫 MongoDB 又寫 Elasticsearch / Redis / data warehouse）換成 change stream → Kafka → downstream sink 後、有了第一版 CDC pipeline、但連續工作幾週後出現「downstream 漏 event」或「duplicate event」；最痛的是 connector restart 後 resume token 過期（oplog 已滾掉）、整個 collection 必須重灌。本文把 change stream 機制、Kafka Connector 配置、resume token 治理、sharded cluster scope 選擇講清楚。

本文不重複 [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) 已寫過的 change streams 簡介 — 而是 production CDC pipeline 部署 + 失敗修復的實作層教學。

> **MongoDB 適用度前置判讀**：進到 CDC pipeline 設計前先確認 workload 在 MongoDB 適用區（document shape 主導 / contract layer 該放哪 / 跨雲 hedging 是否需要）— 詳見 [schema-design-pattern 開頭 3 軸前置判讀](../schema-design-pattern/#問題情境document-自由的後座力)、本篇不重複展開。Change streams 是 *已選 MongoDB 後* 的 event-driven 整合議題。

## 問題情境：第一版 CDC pipeline 跑幾週的踩雷

典型觸發場景：application 寫 MongoDB 後還要 dual-write Elasticsearch / Redis / data warehouse、application code 越塞越多 hook、寫入失敗的補償邏輯散落各處。改用 change stream → Kafka → downstream sink 後、有了第一版 CDC pipeline、但連續工作幾週後出現：

- Downstream 漏 event 或 duplicate event
- Connector restart 後 resume token 過期（oplog 已滾掉）、整個 collection 必須重灌
- Sharded cluster 上 collection-level change stream 跟 cluster-wide change stream 行為不同、application 連 mongos 跟連 single shard 拿到不同 event

讀者徵兆：

- MongoDB Kafka Connector log `ChangeStreamHistoryLost` 或 `ResumeTokenChanged`
- Downstream Kafka topic event count vs source collection write count 不平
- Replication oplog 跟 change stream consumer 的 lag 同時升

Case anchor：CDC pipeline resume token 過期導致全量重灌的具體 incident 細節需未來 case 補完、本文以「常見 failure pattern」+ 容量公式處理、不憑空編造 incident 數字。側面引用 [Spotify Kafka → PubSub migration](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)（pipeline-level migration 經驗對照）。

## 核心機制

Change stream 是 MongoDB 3.6+ 原生 CDC、本質上是 oplog tail 包裝成 cursor API。可以從 collection / database / cluster 三個 scope 開：

- **Collection-level**：監看單一 collection 的變更
- **Database-level**：監看整個 database 的所有 collection
- **Cluster-wide**：監看整個 cluster 的所有 database

Oplog 是 capped collection、預設 size = disk 5% 或 50GB（取較小）。Resume token 對應 oplog entry 的 timestamp + UUID + documentKey。Token 必須對應仍在 oplog 內的 entry — oplog 滾掉就拿不到 token 對應的位置、`ChangeStreamHistoryLost`。

**Resume token 兩種用法**：

- `_id`：每個 event 都帶、application 自己存
- `startAfter` / `resumeAfter` parameter：重啟 cursor 時帶上

**`fullDocument: "updateLookup"`**：update event 預設只給 delta、加這個 option 會額外 query 一次 primary 拿完整 doc；高頻 update 下成本顯著（primary 負擔翻倍）。

**Pre-image / post-image（6.0+）**：可以拿到 update 前的 doc 狀態、需 collection-level option `changeStreamPreAndPostImages: true`。

**Cluster-wide vs collection-level change stream**：

- Cluster-wide 必須打 mongos、event ordering 是 global
- Collection-level 可直接打單 shard、ordering 只在該 shard 內
- Sharded cluster 上 cluster-wide stream 容易把 mongos 變單點瓶頸（所有 shard 的 event 都收斂到 mongos）

**MongoDB Kafka Connector**（Confluent / MongoDB 官方）：

- Source connector：把 change stream → Kafka topic
- Sink connector：把 Kafka topic → MongoDB
- At-least-once 語義、需 application 處理 idempotency

對應 knowledge card：[change-data-capture](/backend/knowledge-cards/change-data-capture/)、[replication-channel](/backend/knowledge-cards/replication-channel/)、[replication-slot](/backend/knowledge-cards/replication-slot/)（MongoDB 沒 slot、概念對照）。

## 操作流程

**Step 1：scope 決策樹**。

| Scope            | 適用條件                                        | 代價                            |
| ---------------- | ----------------------------------------------- | ------------------------------- |
| Collection-level | 單一 collection 的下游 sink、ordering 需求單一  | 多 collection 要多 connector    |
| Database-level   | 多 collection 共享 sink、ordering 跨 collection | filter cost 在 connector 端     |
| Cluster-wide     | 整個 cluster 統一 audit / replay                | mongos 單點瓶頸風險、event 量大 |

**Step 2：oplog sizing**。容量公式：

```text
oplog size >= peak write rate × max acceptable consumer downtime
```

典型設 24-72 小時可恢復窗口。例：peak 5K WPS、想容忍 48 小時 connector down、oplog 至少 5K × 86400 × 2 ÷ docs_per_GB ≈ 看實際 doc size 決定。在 Atlas 上 oplog size 可直接調、自管 cluster 改 `replSetResizeOplog`。

**Step 3：Kafka Connector 配置**。

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

關鍵欄位：

- `change.stream.full.document: "updateLookup"`：每 update 額外 query primary 拿完整 doc（成本意識）
- `copy.existing: "true"`：connector 啟動時先把現有 collection 全量複製、再切到 change stream — 適合初次部署
- `errors.tolerance: "none"`：sink 失敗時 batch 停在 dead-letter queue、不 silently drop

**Step 4：resume token persistence**。Connector 把 token 寫 Kafka `__consumer_offsets` 或外部 store；application 自管 change stream 時要寫到 durable store（不是 in-memory）。

**Step 5：filter pipeline**。Change stream 支援 aggregation pipeline 把過濾下推到 MongoDB：

```javascript
const pipeline = [
  { $match: { "operationType": { $in: ["insert", "update", "delete"] } } },
  { $match: { "fullDocument.region": "ap-tokyo" } }
]
const changeStream = db.orders.watch(pipeline)
```

把過濾下推減少 connector 處理量、特別是高頻 collection 上。

**Step 6：downstream idempotency**。Sink 收 Kafka event 時用 `documentKey._id + clusterTime` 做 dedup key — at-least-once 語義意味著 connector restart 後幾分鐘 event 會重發。

驗證點：

- Source collection write count vs Kafka topic event count 差異 < 0.1%
- Resume token age < oplog retention 的 50%（健康狀態）
- Connector restart drill 能 5 分鐘內接回

Rollback boundary：source connector 是 read-only 對 MongoDB 無傷；sink connector 要備份 target 才能還原；resume token 寫錯 → 從 `startAtOperationTime` 回退到時間點重跑。

## 失敗模式

**Resume token 過期（oplog 滾掉）**：connector down 太久、oplog 已超出 retention、`ChangeStreamHistoryLost` → 必須 `copy.existing` 全量重灌、期間 downstream 看不到新資料。預防是 oplog sizing 留 buffer + connector lag alarm + token age 監控（age > oplog retention 的 50% 預警）。

**updateLookup 在高頻 update 下打爆 primary**：每筆 update event 都觸發一次 primary query、primary 負擔翻倍。修法是改 collection-level pre/post image（6.0+）、由 MongoDB 自己在寫入時記錄、或在 application 補完整 doc 後再寫 Kafka、不用 updateLookup。

**Sharded cluster cluster-wide stream 打爆 mongos**：所有 shard 的 event 都收斂到 mongos、mongos 變單點瓶頸。修法是改 collection-level stream 多 connector 並行、每 connector 連 mongos 但只訂單一 collection。

**At-least-once 變 duplicate flood**：connector restart 點之後幾分鐘 event 重發、downstream 沒做 idempotency → 重複 side effect（重複發 email、重複扣款）。修法是 sink 端強制 idempotency（dedup key 寫 Redis / DB）、不能假設「我用 at-least-once 但實際不會 duplicate」。

**Schema drift 突然 break sink**：MongoDB 寫了新欄位 / 改型別、sink connector 的 JSON schema 不認、batch 停在 dead-letter queue。修法是 schema 變動有 validation gate（見 [schema design pattern](../schema-design-pattern/)）、sink schema 設 `lenient` 模式吃 unknown field、或加 schema registry 統一版本。

**Backup / DDL 期間 change stream 異常**：`reIndex` / `compact` / `dropCollection` 觸發特殊 event、connector 沒處理 → consumer 停。修法是 connector 處理特殊 event 邏輯要明確、不認得的 operation type 至少 log warning 而不是 silently stuck。

Anti-recommendation：

- 簡單的 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) + application transactional write 對於低吞吐 / 單 sink 的場景比 change stream + Kafka 簡單；不是所有「需要 event 通知」的場景都要 CDC pipeline
- 若 downstream 只是同一 region 同團隊的 Elasticsearch index、`$merge` 寫進中介 collection 或 application 雙寫 + 對賬可能成本更低
- Resume token 過期是這條路徑最痛的事故、oplog sizing 是 *投資而不是成本* — 不要為了省 storage 把 oplog 設太小

## 容量與觀測

關鍵 metric：

- **Oplog 健康**：oplog 寫入速率與保留時間
- **Change stream 健康**：cursor age、resume token 距 oplog 頭尾的距離
- **Connector 健康**：connector lag（Kafka offset 對比 source write）
- **下游健康**：event count diff（source write count vs sink apply count）、event time → arrival time lag 分布

Mongo command：

- `db.getReplicationInfo()`：oplog 大小 / 時間範圍
- `db.printReplicationInfo()`：oplog 摘要
- `db.currentOp({ "op": "getmore", "ns": "local.oplog.rs" })`：看 change stream consumer 連線

Connector metric（Kafka Connect JMX）：`source-record-poll-rate`、`source-record-write-rate`、`offset-commit-success-rate`。

回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：oplog retention + connector lag + dedup rate 是 CDC pipeline 健康狀態 evidence 三件套。

回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：CDC lag 升高時區分 (a) source oplog 寫太快 (b) connector 處理慢 (c) downstream sink 慢。

## 邊界與整合

Sibling deep articles：

- [shard key selection](../shard-key-selection/) — cluster-wide vs collection-level change stream 在 sharded cluster 的選擇
- [replica set read preference](../replica-set-read-preference/) — change stream 對 primary load 的影響、能否走 secondary
- [schema design pattern](../schema-design-pattern/) — schema validator 對下游 sink 的契約意義
- [connection management and cache layer](../connection-management-and-cache-layer/) — CDC sink 在 production 跨層架構裡的角色（cache invalidation / federated DB 同步）

Migration playbook：

- MongoDB → 其他 sink 的 bulk migration 走 [→ Atlas Migration Service](/backend/01-database/vendors/mongodb/migrate-to-atlas/)
- 遷出 MongoDB 時 change stream 是 catch-up 機制（先 bulk export、再 change stream 補增量）

跟 1.x 互引：[1.7 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 處理 schema drift 時 CDC pipeline 的[對賬](/backend/knowledge-cards/data-reconciliation/)；[1.9 reconciliation data repair](/backend/01-database/reconciliation-data-repair/) 處理 CDC 失準後的對賬流程。

## 相關連結

- [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) — 本文是該頁尾「change streams + Kafka」backlog 的深度展開
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/)
- 官方：[Change Streams](https://www.mongodb.com/docs/manual/changeStreams/)、[MongoDB Kafka Connector](https://www.mongodb.com/docs/kafka-connector/current/)、[Oplog](https://www.mongodb.com/docs/manual/core/replica-set-oplog/)
