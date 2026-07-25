---
title: "SQLite Local-first Sync Boundary"
date: 2026-05-21
description: "SQLite local-first app、multi-device sync、server authority、conflict resolution、delete propagation 與 offline-first trade-off"
tags: ["backend", "database", "sqlite", "local-first", "sync", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 適合 local-first / offline-first 場景；本文聚焦 *SQLite local store 與 multi-device sync protocol 的責任分界*。

SQLite local-first sync boundary 的核心責任是把「本機可用」和「多端一致」分成兩個問題。SQLite 很適合保存 device-local state；但它不提供 identity、transport、[conflict resolution](/backend/knowledge-cards/conflict-resolution/)、delete propagation、server authority 或 audit trail。當資料要跨裝置、跨使用者或跨服務同步時，SQLite 只是 local replica / working copy。

本文的判讀錨點是：[local-first](/backend/knowledge-cards/local-first/) 的產品價值來自離線可用，工程成本來自同步語意。SQLite 解的是 local durability；sync layer 解的是資料合併、順序、權威來源與錯誤修復。

## Local state taxonomy

Local-first 設計的第一步是標記本機資料角色。不同資料角色對 sync、backup、conflict 與 delete 的要求不同。

| 資料角色              | 例子                                   | Sync 語意                               |
| --------------------- | -------------------------------------- | --------------------------------------- |
| Local cache           | API response cache、thumbnail metadata | 可清除、可重抓                          |
| Draft / working copy  | 草稿、離線表單、未送出 action          | 需要 upload / retry / conflict handling |
| Local source of truth | 單裝置日記、CLI state                  | 需要 backup / export，可能不需要 server |
| Local replica         | server record 的本地副本               | server authority、stale read、sync lag  |
| Sync queue            | pending mutation / event log           | ordering、idempotency、replay           |

這張表的重點是資料角色先於 sync 工具。若所有資料都只是 cache，SQLite + TTL 足夠；若有 pending mutation 或 multi-device edit，就需要 sync protocol。

## Authority boundary

Authority boundary 的核心責任是決定衝突時誰說了算。Local-first app 可以讓 device、server、field-level merge 或 CRDT 成為不同層的 authority；SQLite 本身只保存狀態，不替系統決策。

| Authority model      | 適合情境                    | 代價                                |
| -------------------- | --------------------------- | ----------------------------------- |
| Server authority     | 帳務、權限、共享資料        | 離線寫入要排隊，回線後可能被拒絕    |
| Device authority     | 單使用者、單裝置資料        | 多裝置同步能力弱                    |
| Last-write-wins      | 低價值設定、簡單 preference | 資料覆蓋風險                        |
| Field merge          | profile、表單、可分欄位資料 | merge rule 要測，使用者理解成本上升 |
| CRDT / operation log | 協作編輯、順序敏感操作      | 實作與除錯成本高                    |

Authority model 要和 product semantics 對齊。庫存、付款、權限這類資料通常需要 server authority；notes、draft、local settings 可以接受更偏 local 的權威模型。

## Sync transport 與 local log

Sync transport 的核心責任是把 SQLite local state 轉成可重送、可去重、可驗證的資料流。最常見做法是本地維護 pending mutation table 或 change log，再由 background sync worker 送到 server。

```sql
CREATE TABLE pending_mutations (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);
```

| 設計點                                                          | 判讀                                      |
| --------------------------------------------------------------- | ----------------------------------------- |
| idempotency                                                     | 每個 mutation 需要穩定 id，避免重送副作用 |
| ordering                                                        | 同 entity 操作是否必須按順序              |
| retry                                                           | transient failure、backoff、dead-letter   |
| compaction                                                      | 已同步 local log 何時清除                 |
| [reconciliation](/backend/knowledge-cards/data-reconciliation/) | server / local 差異如何修復               |

這裡和 backend queue 概念相通：pending mutation table 是本機版 durable queue。它需要 [idempotency](/backend/knowledge-cards/idempotency/)、retry 與 replay 思維，而不只是「存一張表」。

## Conflict resolution

Conflict resolution 的核心責任是讓兩個合法 local write 合併成可接受狀態。SQLite 可以保存 local write；sync layer 要決定衝突偵測、呈現與合併。

| 衝突型態              | 例子                          | 處理策略                         |
| --------------------- | ----------------------------- | -------------------------------- |
| Same field update     | 兩台裝置改同一個 display name | LWW、server reject、manual merge |
| Disjoint field update | 一台改 phone，一台改 address  | field merge                      |
| Delete vs update      | 一台刪除，一台修改            | tombstone、manual review         |
| Ordered operation     | task reorder、ledger append   | operation log、server sequence   |

Conflict policy 要在資料模型設計時決定。等衝突發生後才補策略，通常會導致資料修復、客服流程與 audit evidence 同時缺位。

## Delete propagation 與 privacy

Delete propagation 的核心責任是讓 server、device、backup 與 sync queue 對「刪除」有一致語意。Local-first app 常見風險是 server 已刪，但 device local DB、pending queue 或 OS backup 還留著資料。

| 刪除語意    | 適合情境                    | SQLite 設計                                      |
| ----------- | --------------------------- | ------------------------------------------------ |
| Soft delete | 可恢復、需要 sync tombstone | `deleted_at`、sync tombstone、retention job      |
| Hard delete | privacy / compliance        | local purge、backup exclusion、sync confirmation |
| Redaction   | support bundle / log        | export 時遮罩 sensitive fields                   |

刪除在同步系統裡是一個跨裝置生命週期。若資料跨裝置同步，delete 需要 [tombstone](/backend/knowledge-cards/tombstone/)、ack、retry、backup retention 與 evidence；這些責任要接到 [Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)。

## Production 踩雷

### Case 1：pending mutation 沒有 idempotency key

Pending mutation 沒有 idempotency key 的核心風險是重送造成重複副作用。網路 timeout 後 worker 重送，server 已經處理第一次請求，第二次又建立一筆資料或扣一次庫存。

修正方向是每個 mutation 生成 stable id，server 以 idempotency key 去重，local SQLite 保存 retry state 與 server ack。

### Case 2：LWW 覆蓋使用者資料

Last-write-wins 的核心風險是把衝突靜默變成資料遺失。Preference 類資料可接受；草稿、文件、表單、付款資料通常需要更清楚的 conflict handling。

修正方向是依資料價值分層。低價值設定用 LWW；高價值內容用 field merge、manual conflict 或 operation log。

### Case 3：delete 沒傳到離線裝置

Delete propagation 失敗的核心風險是 privacy / compliance 失效。使用者刪除 server 資料後，一台長期離線裝置重新上線又把舊資料同步回來。

修正方向是 tombstone + server authority。Server 要能拒絕過期 mutation，device 要能接收 delete tombstone 並 purge local state。

## 操作檢查清單

Local-first SQLite 設計要回答：

1. 哪些 table 是 local source of truth，哪些是 server replica。
2. Pending mutation 是否有 idempotency key 與 retry state。
3. Conflict policy 是 LWW、field merge、manual merge 還是 operation log。
4. Delete 是否有 tombstone、ack 與 local purge。
5. Sync worker 是否有 backoff、dead-letter、reconciliation。
6. Device backup 是否會保存已刪資料。
7. Server 是否能拒絕過期 local write。

## 下一步路由

- 上游：[Mobile / Desktop Embedded Store](/backend/01-database/vendors/sqlite/mobile-desktop-embedded-store/)
- Sibling：[SQLite to D1 / Turso](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)、[D1 / Turso / libSQL Comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/)
- 卡片：[Idempotency](/backend/knowledge-cards/idempotency/)、[Eventual Consistency](/backend/knowledge-cards/eventual-consistency/)、[Stale Read](/backend/knowledge-cards/stale-read/)
- 跨模組：[Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)
