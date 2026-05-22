---
title: "PostgreSQL Logical Decoding Plugins"
date: 2026-05-22
description: "PostgreSQL logical decoding output plugin、pgoutput、wal2json、test_decoding、CDC connector 與 plugin 選型"
tags: ["backend", "database", "postgresql", "cdc", "logical-decoding"]
---

PostgreSQL logical decoding plugins 的核心責任是把 WAL 中的變更轉成外部消費者可理解的事件格式。PostgreSQL 官方 logical decoding 文件說明，logical decoding 透過 replication slot 將 WAL 變更解碼成 plugin output；output plugin 決定外部看到的是 PostgreSQL protocol、JSON、測試文字或自訂格式。

本文的判讀錨點是：plugin 選型是 CDC contract 決策。它影響 schema evolution、事件欄位、delete 表示、transaction boundary、consumer compatibility、slot lag 與故障復原。

## Plugin Boundary

Plugin boundary 的核心責任是定義 database 變更如何離開 PostgreSQL。常見選項包含內建 `pgoutput`、測試用 `test_decoding`、JSON-oriented plugin，以及 Debezium connector 支援的 plugin / protocol。

| Plugin / path       | 主要責任                                | 適合情境                                        |
| ------------------- | --------------------------------------- | ----------------------------------------------- |
| `pgoutput`          | PostgreSQL logical replication protocol | built-in logical replication、Debezium 常見路線 |
| `test_decoding`     | 人類可讀測試 output                     | lab、debug、教育用途                            |
| `wal2json`          | JSON change event                       | 自訂 consumer、legacy CDC                       |
| decoderbufs         | Protobuf event                          | 強 schema contract 的 pipeline                  |
| Native subscription | DB-to-DB replication                    | PostgreSQL 之間 table replication               |

`pgoutput` 適合標準化 CDC。它與 publication / subscription model 對齊，能保留 PostgreSQL logical replication 的主路線。

`test_decoding` 適合教學與排錯。它讓人看到 transaction 裡發生的 insert / update / delete，但它的定位是測試與理解，不應作為正式 event contract。

## Replication Slot Responsibility

Replication slot responsibility 的核心責任是保護 consumer 進度，同時管理 WAL retention。Logical slot 會讓 PostgreSQL 保留尚未被 consumer 確認的 WAL；consumer 停住時，slot lag 會轉成 disk pressure。

| Signal                 | 意義                       | 操作反應                             |
| ---------------------- | -------------------------- | ------------------------------------ |
| `confirmed_flush_lsn`  | consumer 已確認的位置      | 用來判斷 CDC 進度                    |
| retained WAL size      | slot 造成的 WAL 保留量     | alert、調整 consumer、drop / advance |
| inactive slot          | consumer 離線              | 檢查 connector、暫停 release         |
| publication table diff | CDC scope 與 schema 不一致 | review publication / table ownership |

Slot 是 production resource。每個 logical slot 都要有 owner、consumer、SLO、drop condition、backfill plan 與 alert。

## Event Contract

Event contract 的核心責任是讓 downstream 知道每個變更代表什麼。CDC 事件至少要說明 key、before/after image、operation、commit timestamp、transaction ordering、schema version 與 delete representation。

| Contract 面向    | 審查問題                                    |
| ---------------- | ------------------------------------------- |
| Key              | table 是否有 replica identity / primary key |
| Update image     | 是否需要 before value                       |
| Delete           | tombstone、key-only delete、soft delete     |
| Ordering         | transaction order 是否要保留                |
| Schema evolution | 新欄位、rename、drop 欄位如何通知           |
| Backfill         | initial snapshot 與 streaming 如何銜接      |

Replica identity 是 CDC 的核心設定。沒有穩定 key 的 table 會讓 update / delete event 難以被 downstream 正確套用；這類 table 要先補 primary key 或明確設定 replica identity。

## Connector Patterns

Connector patterns 的核心責任是把 plugin output 接到實際 pipeline。Debezium、custom consumer、DB native subscription 的維運責任不同。

| Pattern             | 優點                               | 風險                                       |
| ------------------- | ---------------------------------- | ------------------------------------------ |
| Debezium connector  | 成熟 snapshot + streaming workflow | connector state、Kafka / offset operation  |
| Native subscription | PostgreSQL 原生 DB-to-DB           | schema drift、DDL coordination             |
| Custom consumer     | 可客製 event contract              | slot management 與 error handling 自行負責 |
| Batch export + CDC  | backfill 與 streaming 分開         | cutover LSN 與 duplication handling        |

Connector 要定義 backfill 與 streaming 的接點。最常見的事故是 snapshot 還沒完成就開始消費、或 cutover LSN 沒有被記錄，導致 downstream 重複或漏資料。

## Failure Modes

Failure modes 的核心責任是把 CDC 事故分成 database、connector、schema 與 downstream 四層。

| Failure mode    | 判讀訊號                       | 第一反應                              |
| --------------- | ------------------------------ | ------------------------------------- |
| Slot lag growth | retained WAL 持續增加          | 暫停重型寫入、修 connector、評估 drop |
| Schema break    | connector 解析失敗             | 停止 DDL rollout、補 schema evolution |
| Missing key     | update / delete 缺少可套用 key | 修 replica identity / key contract    |
| Duplicate event | consumer 重啟或 offset 回退    | idempotent consumer                   |
| Downstream slow | Kafka / sink lag 增加          | 擴 sink、調 batch、保護 slot          |

Slot lag 是最高優先訊號，因為它會占用 PostgreSQL WAL storage。Runbook 要有「何時暫停 producer」、「何時 drop slot」、「如何重建 snapshot」的明確門檻。

## Selection Checklist

Selection checklist 的核心責任是讓 plugin 選型可審查。

1. Downstream 需要 DB-to-DB replication、JSON event、Protobuf event 還是 connector-managed event。
2. 每張 table 是否有 stable key 與 replica identity。
3. Initial snapshot 如何銜接 streaming。
4. Schema evolution 如何通知 consumer。
5. Slot lag、connector lag、sink lag 如何告警。
6. Consumer 是否 idempotent。
7. Disaster recovery 後 slot / offset 如何重建。

完成這份 checklist 後，再決定 plugin 與 connector。CDC 的成功標準是 downstream 能長期維持正確資料，而不只是成功建立 slot。

## 下一步路由

Logical decoding plugins 完成後，實作 CDC pipeline 讀 [Logical Replication / Debezium](../logical-replication-debezium/)；slot 維運讀 [Replication Slot Management](../replication-slot-management/)；跨資料庫搬遷讀 [Database Migration Playbook](/backend/01-database/database-migration-playbook/)。
