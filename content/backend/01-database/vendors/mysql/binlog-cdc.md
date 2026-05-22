---
title: "MySQL Binary Log + CDC：Maxwell / Debezium 是 binlog 第二消費者"
date: 2026-05-19
description: "MySQL CDC 跟 PostgreSQL logical decoding 是不同 abstraction — PG logical decoding 是 *logical event*（INSERT / UPDATE / DELETE）、MySQL CDC 是 *讀 binlog row-level event*。Maxwell / Debezium 是 binlog 第二消費者（跟 replica 共享 binlog stream），並非 PostgreSQL 式 logical replication 系統。本文走 binlog 三種 format（STATEMENT / ROW / MIXED）、ROW format 的 raw event 結構、Maxwell vs Debezium 對比、配置 step-by-step、5 production 踩雷（binlog retention / DDL event / row image / Kafka producer 跟 binlog reader 速度差 / schema change 跟 CDC consumer 同步）"
weight: 17
tags: ["backend", "database", "mysql", "binlog", "cdc", "debezium", "maxwell", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *CDC* — Maxwell / Debezium 怎麼讀 binlog 產生 event stream。

---

MySQL CDC 的核心定位是 *binlog consumer*。

這個誤解來自跟 PostgreSQL CDC（[Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)）混用名詞。PG 的 logical decoding 是 *MySQL 沒有的能力* — PG 有 logical event（INSERT / UPDATE / DELETE 加上欄位 metadata）、輸出格式是 logical（人可讀、schema-aware）。MySQL 的 binlog 是 *physical* — 紀錄的是 row 的 binary image、不帶 schema 資訊。

Maxwell / Debezium 對 MySQL 是 *binlog 第二消費者*：

```text
Primary MySQL → binlog
              ├→ Replica 1（讀 binlog 同步）
              ├→ Replica 2
              └→ Maxwell / Debezium（讀 binlog 解析、發 Kafka）
```

跟 replica 同一份 binlog stream，並非 separate logical decoding output。這個結構決定 CDC consumer 的設計：必須 *自己處理 schema*（從 information_schema 拉、跟 binlog event 對齊）、必須 *自己 track position*（binlog file + position 或 GTID）。

## Binlog format：STATEMENT / ROW / MIXED

MySQL binlog 有 3 種 format、CDC 只能用 ROW：

| Format    | 紀錄內容                               | CDC 可用？                       |
| --------- | -------------------------------------- | -------------------------------- |
| STATEMENT | 原始 SQL statement                     | 不可用（CDC 看不到實際改的 row） |
| ROW       | 每個改變的 row（before + after image） | CDC 標準                         |
| MIXED     | 預設 STATEMENT、特殊情況用 ROW         | 不推薦（CDC 行為不一致）         |

ROW 是 CDC 唯一選擇、production 強制：

```ini
binlog_format = ROW
binlog_row_image = FULL  # FULL (all columns) / MINIMAL (only changed) / NOBLOB
log_bin_use_v1_row_events = 0  # 用新版 event format
```

`binlog_row_image` 取捨：

- `FULL`：每個 row event 包含所有 column（before + after）、binlog 大、CDC 完整
- `MINIMAL`：只包含 changed column + primary key、binlog 省 30-50% 空間、CDC 看不到 *未變 column*
- `NOBLOB`：跟 FULL 一樣但 BLOB / TEXT column 只在 changed 時包含、平衡選擇

對 *CDC 需要 full row payload*（例如下游 search index 重建）必須 `FULL`。對 *純 audit log* 可以 `MINIMAL`。

## ROW format 的 raw event 結構

Binlog ROW event 的資料形狀是 *binary row image*，而非 *INSERT INTO orders VALUES (1, 'foo', 100)*：

```text
TABLE_MAP_EVENT     - 對應 table schema metadata (table id + column type)
                      ↓ 接續同一個 transaction 內所有 row event
WRITE_ROWS_EVENT    - INSERT 的新 row image（column values）
UPDATE_ROWS_EVENT   - UPDATE 的 before + after image
DELETE_ROWS_EVENT   - DELETE 的 row image（被刪的 row）
XID_EVENT           - transaction commit marker
```

CDC consumer（Maxwell / Debezium）必須：

1. 接收 binlog event stream
2. 看到 `TABLE_MAP_EVENT` 從中拿 table id → 對應 table name（cache 一份）
3. 看到 `WRITE/UPDATE/DELETE_ROWS_EVENT` 用 table id 反查 schema、把 binary 解析成 column value
4. 包成 JSON / Avro / Protobuf 推到 Kafka

關鍵：*table schema 不在 binlog 內*、CDC consumer 必須 *獨立查 information_schema*。如果 schema 變了（ALTER TABLE）、CDC 必須 invalidate cache、重新查、否則新 column 的 row event 解析錯亂。

## Maxwell vs Debezium

兩個是 MySQL CDC 主流選擇、不同設計取捨：

| 維度            | Maxwell                              | Debezium MySQL                                     |
| --------------- | ------------------------------------ | -------------------------------------------------- |
| 開發者          | Zendesk                              | Red Hat                                            |
| 語言            | Java（單一 binary）                  | Java（Kafka Connect plugin）                       |
| 部署模式        | Standalone process                   | Kafka Connect cluster                              |
| 支援 DB         | MySQL only                           | MySQL / PostgreSQL / MongoDB / SQL Server / Oracle |
| Output format   | JSON（內建）                         | JSON / Avro / Protobuf（Kafka Connect）            |
| Producer        | Kafka / Kinesis / RabbitMQ / Pub/Sub | Kafka（Kafka Connect 限制）                        |
| Schema registry | 不支援                               | 支援（Confluent Schema Registry / Apicurio）       |
| Transformation  | filter / stream-level（內建）        | Single Message Transform (SMT)                     |
| Bootstrapping   | 一個 utility 從 `SELECT *` snapshot  | Built-in snapshot mode                             |
| GTID 支援       | 支援                                 | 支援                                               |
| 簡單性          | 高（單一 binary）                    | 中（Kafka Connect 框架成本）                       |

選擇邏輯：

- *只用 MySQL + 想要 simple operations* → Maxwell
- *已用 Kafka Connect、需要 schema registry、跨多種 DB* → Debezium
- *需要 Avro / Protobuf schema 嚴格 governance* → Debezium

## 配置 step-by-step（Debezium MySQL connector）

Debezium 是 Kafka Connect plugin、整套 stack：

```yaml
# debezium-mysql.json - 部署到 Kafka Connect REST API
{
  "name": "orders-mysql-connector",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "database.hostname": "primary.example.com",
    "database.port": "3306",
    "database.user": "debezium",
    "database.password": "...",
    "database.server.id": "184054",          # 唯一 server ID (跟 MySQL replica 一樣)
    "topic.prefix": "production",            # Debezium 2.x（舊 1.x 用 database.server.name）
    "database.include.list": "orders_db",
    "table.include.list": "orders_db.orders,orders_db.payments",

    "database.history.kafka.bootstrap.servers": "kafka:9092",
    "database.history.kafka.topic": "dbhistory.orders",
    "include.schema.changes": "true",

    "snapshot.mode": "initial",              # 或 schema_only / when_needed / never
    "snapshot.locking.mode": "minimal",      # 避免 FLUSH TABLES WITH READ LOCK

    "gtid.source.includes": "...",           # 可選 GTID filter
    "tombstones.on.delete": "true",          # DELETE event 同 partition 跟一個 null tombstone
    "decimal.handling.mode": "double"        # DECIMAL 處理: precise / string / double
  }
}
```

deploy：

```bash
curl -X POST -H "Content-Type: application/json" \
  --data @debezium-mysql.json \
  http://kafka-connect:8083/connectors
```

Output topic：`production.orders_db.orders` / `production.orders_db.payments` 等 — 每張 table 一個 topic。

## 配置 step-by-step（Maxwell）

Maxwell 簡單很多：

```bash
maxwell \
  --host=primary.example.com \
  --user=maxwell \
  --password=... \
  --producer=kafka \
  --kafka.bootstrap.servers=kafka:9092 \
  --kafka_topic="maxwell.%{database}.%{table}" \
  --filter='exclude: *.*, include: orders_db.*' \
  --gtid_mode=true \
  --output_ddl=true \
  --output_xoffset=true
```

Maxwell event format：

```json
{
  "database": "orders_db",
  "table": "orders",
  "type": "update",
  "ts": 1715000000,
  "xid": 12345,
  "commit": true,
  "data": { "id": 1, "status": "shipped", "amount": 100.50 },
  "old": { "status": "pending" }
}
```

Debezium 對應的 event 格式更複雜（envelope + before + after + source + ts_ms 各 nested）、但跟 schema registry 整合好。

## 5 個 Production 踩雷

### 1. Binlog retention 太短 — CDC consumer 落後就 re-bootstrap

CDC consumer 失聯（Kafka Connect cluster down、network issue）超過 binlog retention（預設 `binlog_expire_logs_seconds=2592000`、30 天、但有些 production 縮短到 1 天）、需要的 binlog event 已被 purge、consumer error。

修法：

- *Production binlog retention >= 7 天*（避免為了 disk 過度縮短）
- 監控 `Master_Log_File` 是否還在（如果 retention 設 7 天、確認當前 file 仍存在）
- CDC consumer 失聯 alert 設 *早於 retention 期*（例如 6 天告警、給 24 小時修）
- 真的 missed binlog、必須 *re-snapshot table*（用 Debezium `snapshot.new.tables`）— 24 小時級工作

### 2. DDL event 處理 — schema change 跟 row event 對齊

`ALTER TABLE orders ADD COLUMN status VARCHAR(20)` 之後、`UPDATE_ROWS_EVENT` 多一個 column。CDC consumer 如果還用舊 schema cache、解析 row 時欄位數對不上、event 丟。

修法（Debezium）：

- `include.schema.changes=true`：DDL 進獨立 topic、consumer 監聽更新自己的 schema cache
- `database.history.kafka.topic`：Debezium 自己 track schema 歷史

修法（Maxwell）：

- `--output_ddl=true`：DDL 也進 stream、downstream 看到 DDL event 自己更新
- 沒有內建 schema history、要 *application 層處理*

修法（兩者通用）：

- 用 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/) 取代直接 ALTER — 工具操作的 DDL 對 CDC consumer 更可預期
- Schema 改動 *優先 add column 為 nullable*、避免 backfill 期間 CDC consumer 看到 mid-state

### 3. `binlog_row_image=MINIMAL` 讓下游錯亂

`MINIMAL` 省 binlog 空間、但 row event 只含 changed column。下游 *search index 重建* 需要 *full row payload* 的場景下、`MINIMAL` 看不到未變的 column、index 缺欄位。

修法：

- CDC 需要 full payload 的場景 *必須 `FULL`*、這項成本要納入容量規劃
- 如果空間真緊、考慮 `NOBLOB`（BLOB / TEXT 只在 changed 時包含、其他 column 仍 FULL）
- *統一設定*：production 全部 server 同一 binlog_row_image 設定

### 4. Kafka producer 跟 binlog reader 速度差 — lag 累積

Binlog reader 從 MySQL 讀 1000 event/sec、Kafka producer 寫得只有 800 event/sec、CDC consumer 自身 lag 累積、最終 disk 滿（producer 內部 buffer）。

修法：

- 監控 *CDC consumer lag*：對 Debezium 看 Kafka Connect 的 `source-record-poll-rate` vs `source-record-write-rate`
- Kafka producer tuning：`batch.size` / `linger.ms` / `compression.type=snappy`
- Kafka broker capacity：partition 數量 ≥ Debezium task 數量、避免 partition 瓶頸
- 避免把 *過多 table* 給單一 Debezium connector — 用 *table grouping*（按 traffic 拆 connector）

### 5. Schema change 跟 downstream consumer 不同步

CDC producer（Debezium）正確處理了 schema change、但 *downstream Kafka consumer* 用舊 schema deserialize、新 column 看不到 / type 解析錯。

修法：

- 用 *Schema Registry*（Confluent / Apicurio）+ Avro：consumer 訂閱 schema、自動 evolve
- 不用 schema registry 時、CDC payload 設計 *backward-compatible*（新 column 為 optional）
- *Application 層 schema change protocol*：[Expand / Contract](/backend/knowledge-cards/expand-contract/) — 先加 column、deploy consumer 認 column、再 backfill、最後 application 寫新 column
- 大型 schema change 跨多服務、建議 *先 freeze CDC stream、做 schema migration、resume stream*（極端但確定）

## 容量規劃要點

| 元件                       | 容量考量                                                                     |
| -------------------------- | ---------------------------------------------------------------------------- |
| MySQL binlog disk          | retention × 寫吞吐 × event size（5K WPS × 1 KB × 7 天 ~= 3 GB / 天 = 21 GB） |
| Debezium / Maxwell process | 1 vCPU + 2-4 GB RAM（per connector、視 throughput）                          |
| Kafka topic partition      | 每 table 1-10 partition（依寫吞吐）、保 key-based ordering                   |
| Kafka 保留期               | 7-30 天（讓 downstream consumer 有 recover window）                          |
| Schema Registry            | < 100 MB storage、replicate 跨 3 broker                                      |

對 100K WPS server、CDC pipeline cost 大致是 *MySQL infra 的 5-10%*。

## 跟其他模組整合

### 跟 Replication topology

CDC 是 *binlog 第二消費者*、需要 *GTID + binlog ROW format*（[Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)）。Debezium / Maxwell 都偏好從 *replica* 讀 binlog（不增加 primary 負擔）、但要小心 replica lag 加在 CDC lag 上。

### 跟 OSC tool

[gh-ost / pt-osc](/backend/01-database/vendors/mysql/online-schema-change-tools/) 跑 schema change 時、會在 binlog 留下大量 row event（copy 既有 row 到 ghost）。CDC consumer 看到這些 event *是 normal-looking INSERT*、可能誤觸發 downstream side effect。

修法：

- CDC consumer 過濾 *ghost table prefix*（`_orders_new` / `_orders_gho`）— 不發 downstream
- 或暫停 CDC 期間跑 OSC（用 Debezium pause API）

### 跟 PostgreSQL Logical Replication + Debezium

| 維度            | MySQL（binlog）                                   | PostgreSQL（logical decoding）                              |
| --------------- | ------------------------------------------------- | ----------------------------------------------------------- |
| 抽象層          | Physical（row binary）                            | Logical（row + schema-aware）                               |
| Schema metadata | 不在 event 內、要查 information_schema            | 在 event 內（plugin output）                                |
| DDL handling    | DDL 本身是 binlog event                           | DDL 不在 logical decoding output（要 trigger 自己 capture） |
| 啟用成本        | binlog ROW + GTID（基本 MySQL replication setup） | logical replication slot + publication                      |
| Snapshot        | `SELECT *` + binlog catchup                       | logical replication initial sync                            |

詳見 [PostgreSQL Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) — 這是 sibling 對照，用來區分不同 abstraction。

### 跟 Aurora MySQL

Aurora MySQL 5.7 / 8.0 都支援 binlog + GTID、CDC 可用。但 Aurora 推薦走 *Aurora-native database activity streams*（不同 abstraction）— 跟 Debezium 共存但有 overlapping。生產上 Debezium 仍是 cross-cloud 跟 vendor-neutral 選項、優先用 Debezium。

詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

## Production case：Shopify sharded MySQL CDC

Sharded MySQL CDC 的核心責任是把多個 shard 的 binlog 轉成可消費、可回放、可觀測的事件流。[Shopify Debezium CDC over sharded MySQL](/backend/03-message-queue/cases/kafka-shopify-debezium-cdc/) 提供的工程訊號是 100+ shard、約 150 個 Debezium connector、BFCM 期間 100K records/sec，以及 snapshot lock 與 oversized payload 對 CDC pipeline 的壓力。

這個案例要回收到三個操作判準。第一，connector 數量應跟 shard 拓撲一起設計，避免單一 connector 變成跨 shard bottleneck。第二，snapshot window 要排進 schema migration 與 event consumer 的變更計畫，避免 initial snapshot 把 production read path 壓滿。第三，oversized payload 要在 schema / outbox / topic 分流階段處理，避免 Kafka partition 與 downstream consumer 同時承受大訊息。

Shopify 案例的下一步路由是把本篇和 [Database Sharding](/backend/knowledge-cards/database-sharding/) 一起讀。若讀者關心 broker 層的 partition、consumer lag 與 replay 策略，接到 [Kafka vendor](/backend/03-message-queue/vendors/kafka/)；若關心資料庫端壓力，回到 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/) 與 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（binlog ROW + GTID 是 CDC pre-requisite）
- [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)（OSC + CDC 整合）
- [PostgreSQL Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)（PG sibling、不同 abstraction）
- [Outbox pattern 卡片](/backend/knowledge-cards/outbox-pattern/)（CDC 跟 outbox 在 application-level event publishing 的關係）
- [Expand / Contract 卡片](/backend/knowledge-cards/expand-contract/)（schema migration 跟 CDC consumer）
- 官方：[Debezium MySQL Connector](https://debezium.io/documentation/reference/stable/connectors/mysql.html) / [Maxwell](https://maxwells-daemon.io/)
