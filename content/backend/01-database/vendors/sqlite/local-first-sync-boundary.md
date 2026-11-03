---
title: "SQLite Local-first Sync Boundary"
date: 2026-05-21
description: "SQLite local-first app、multi-device sync、server authority、拉取變更的接續標記（updated_at 漏列與 server 版本號）、第一次同步的分批、tombstone 保留期限與全量重新同步、conflict resolution、delete propagation 與 offline-first trade-off"
tags: ["backend", "database", "sqlite", "local-first", "sync", "deep-article"]
---

SQLite local-first sync boundary 的核心責任是把「本機可用」和「多端一致」分成兩個問題。SQLite 很適合保存 device-local state；但它不提供 identity、transport、[conflict resolution](/backend/knowledge-cards/conflict-resolution/)、delete propagation、server authority 或 audit trail。當資料要跨裝置、跨使用者或跨服務同步時，SQLite 只是 local replica / working copy。

本文的範圍是 [local-first](/backend/knowledge-cards/local-first/) app 裡 SQLite local store 與 sync layer 的責任分界：SQLite 負責 local durability，sync layer 負責資料合併、順序、權威來源與錯誤修復；各節依序處理本機資料角色、衝突時的 authority model、pending mutation 的傳送、裝置從 server 拉取變更時記下的接續標記（cursor），包括它用時間戳還是 server 遞增的版本號、第一次同步上萬筆時怎麼分批、tombstone 過了保留期限之後怎麼辦、conflict resolution 與 delete propagation。

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

Authority boundary 的核心責任是決定衝突時誰說了算。Local-first app 可以依資料角色，讓 device、server、field-level merge 或 CRDT 分別成為那一類資料的 authority；SQLite 本身只保存狀態，不替系統決策。

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

Pending mutation table 和 backend queue 的概念相通：它是本機版 durable queue。它需要 [idempotency](/backend/knowledge-cards/idempotency/)、retry 與 replay 思維，而不只是「存一張表」。

## 拉取方向：接續標記的欄位、第一次同步與 tombstone 的保留期限

拉取方向的接續標記（cursor）是裝置記下的一個位置，下一次同步時 server 只回傳排在這個位置之後的列。裝置往 server 送的變更，由〈Sync transport 與 local log〉那一節的 pending mutation table（本機的待送佇列）排隊；server 往裝置送的變更由裝置主動拉取，裝置每次拉取都帶著接續標記，server 依接續標記取出一批變更回傳，裝置寫進本機 SQLite 之後把接續標記往前移。接續標記選錯欄位時，server 會在某些寫入時序下永遠不回傳某幾列，裝置與 server 都不會報錯，裝置上的資料就少了那幾列，直到有人做一次全量比對才發現。

這一節的前提是同步的資料屬於同一個使用者（同一個人的多台裝置）。server 上有多位使用者、或資料可以分享時，拉取的查詢要加上使用者範圍（索引跟著變成以使用者開頭的組合），而分享或權限一改，某一列會對某個裝置「變得看得到」或「不再看得到」，那一列本身的版本號卻沒變，照這一節的接續標記永遠拉不到它；這一類同步範圍的設計不在這一節。

### 用 `updated_at` 當接續標記時漏掉的列

`updated_at` 當接續標記的寫法是 `WHERE updated_at > :last_seen`，它依賴一個前提：server 寫入時間戳的順序，就是那些列變得可以被讀到的順序。這個前提在三種情形下不成立：

- **同一個時間戳有好幾列**：一批寫入在同一毫秒落下五列，裝置拉取時 `LIMIT` 剛好切在第三列，接續標記記下那個時間戳，下一次用 `>` 比較，剩下的兩列永遠不會被回傳。改用 `>=` 的話，每一批都會重複回傳同一個時間戳的列，`LIMIT` 小於同一時間戳的列數時接續標記前進不了。
- **交易的提交順序跟時間戳的順序不同**：server 是多個連線同時寫入的資料庫（PostgreSQL 這類）時，交易 A 在 10:00:01 寫下時間戳、10:00:03 才提交，交易 B 在 10:00:02 寫下、10:00:02 就提交。裝置在 10:00:02.5 拉取，讀到 B，接續標記前進到 10:00:02；A 提交之後，它的時間戳比接續標記早，之後的每一次拉取都跳過它。
- **server 的時鐘往回調**：NTP 校時把系統時間往回撥時，之後寫入的列時間戳比已經回傳過的列還早（[Clock Skew](/backend/knowledge-cards/clock-skew/)）。

### 用 server 遞增的版本號當接續標記

server 只有一個寫入者時（server 端的資料庫是 SQLite，一次只有一個寫入交易；WAL mode 底下仍然是單一 writer，見 [WAL concurrency / locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)），在寫入交易裡遞增的計數器，提交順序就是數字順序。server 是多個連線同時寫入的資料庫時，版本號的來源要另外選，三種來源各自會不會漏列與代價，列在 SQL 範例之後。每一筆寫入在同一個交易裡把計數器加一、把新值寫進被改的列，接續標記改記版本號；同一個交易改了好幾列時那幾列共用一個版本號，所以接續標記寫成版本號加主鍵的組合，比較時把兩欄當成一組值依序比（列值比較，row value），排序鍵跟接續標記一致才是一個全序（理由在 [SQL.12 分頁的排序鍵與接續標記](/backend/01-database/sql/pagination-needs-a-total-order/)，這種接續標記的分頁方式見 [Keyset Pagination](/backend/knowledge-cards/keyset-pagination/)）：

```sql
-- server 端（SQLite 3.49.2 實跑）
CREATE TABLE sync_clock (id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL) STRICT;
INSERT INTO sync_clock VALUES (1, 0);
CREATE TABLE books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  version INTEGER NOT NULL,   -- 最後一次被改時的計數器值
  deleted_at TEXT             -- 軟刪除：刪除也是一次改動，要拿到新的版本號（見 Soft Delete 卡）
) STRICT;
CREATE INDEX books_by_version ON books(version, id);

-- 每一次寫入：計數器加一與改列在同一個交易裡
BEGIN IMMEDIATE;
UPDATE sync_clock SET version = version + 1 WHERE id = 1;
UPDATE books SET deleted_at = '2026-11-03T00:00:00Z',
                 version = (SELECT version FROM sync_clock)
WHERE id = 'b2';
COMMIT;

-- 拉取一批：:last_version、:last_id 是裝置上一批最後一列的值，第一次同步填 0 與 ''
SELECT id, title, version, deleted_at
FROM books
WHERE (version, id) > (:last_version, :last_id)
ORDER BY version, id
LIMIT 500;
```

`EXPLAIN QUERY PLAN` 對最後那一句回報 `SEARCH books USING INDEX books_by_version ((version,id)>(?,?))`：server 從索引上的接續標記位置往後讀 500 列，每一列再回表讀 `title` 與 `deleted_at`（這兩欄不在索引裡）。一批的成本跟批次大小成正比、跟這是第幾批無關，`OFFSET` 則要先掃過前面所有的列，越後面的批次越慢。`BEGIN IMMEDIATE` 讓交易一開始就取得寫入鎖，計數器加一與改列之間沒有別的寫入交易插進來。

server 換成多個連線同時寫入的資料庫（PostgreSQL 這類）時，版本號的來源決定會不會漏列：

- **序列產生器（sequence）**：值在交易裡呼叫 `nextval` 時就決定，不隨提交順序調整，提交順序可能跟數字順序不同，跟 `updated_at` 遇到交易提交順序與時間戳順序不同時一樣會漏列。
- **上面那張單列的 `sync_clock` 計數器表**：`UPDATE` 會鎖住那一列直到交易提交，下一個寫入交易要等前一個提交才拿得到下一個值，所以數字順序仍然是提交順序，不會漏列；代價是所有寫入交易在那一列上排隊，整個資料庫的寫入一次只能過一個，寫入量越大排得越久。這是從 PostgreSQL 的列鎖行為推論的，沒有實跑。
- **資料庫依提交順序輸出的變更紀錄**（PostgreSQL 的 [logical replication](/backend/knowledge-cards/logical-replication/) 這一類，PostgreSQL 端的設定在 [PostgreSQL logical decoding plugins](/backend/01-database/vendors/postgresql/logical-decoding-plugins/)）：同步服務改讀這份紀錄，寫入不必排隊，代價是多一個要維運的元件與資料庫端的複製設定。PowerSync 這類同步引擎接 PostgreSQL 時讀的就是這份紀錄。

### 第一次同步上萬筆資料

第一次同步是接續標記從起點開始的同一個拉取迴圈，差別只在批數。裝置每拿到一批，就在同一個本機交易裡寫入這批資料並更新接續標記；同步中途斷線、App 被系統結束時，本機的資料與接續標記一起停在最後一個提交的批次，下一次從那裡接著拉，不必從頭來。第一次同步進行的期間 server 照常有寫入，那些列拿到的版本號比第一次同步開始時 server 的最大版本號大，排在後面的批次裡，迴圈拉到回傳筆數小於 `LIMIT` 為止。

一萬本書、每本的書目欄位（書名、作者、出版資訊、標籤）以幾百位元組估算，本機 SQLite 裡是幾 MB 的資料；這個量級下，一次同步花的時間由網路往返的次數與每批寫入本機的交易數決定，批次大小決定這兩者的取捨：批次大，往返次數少，單一批次失敗時要重送的資料多；批次小則相反。另一種做法是第一次同步不走分頁，改下載 server 產生的一份 SQLite 快照檔，再把接續標記設成快照當下的版本號，之後走增量拉取：往返只有一次，代價是 server 要產生並保存快照，快照越舊，接著要補的增量越多；這種做法沒有實跑。書封這類大檔不放進同步的列裡，列裡只放檔案的網址或雜湊，畫面要顯示時再另外下載：一張書封就比一整列書目大上幾十倍，放進列裡時每一次書目改動都要重送那張圖。

### tombstone 的保留期限與全量重新同步

增量拉取時，裝置靠[軟刪除](/backend/knowledge-cards/soft-delete/)留下的 [tombstone](/backend/knowledge-cards/tombstone/) 得知「這一列已經刪掉」。上面的範例 SQL 刪除時只改 `deleted_at`，列裡的書名還在；刪除的理由是隱私或合規時，tombstone 只留主鍵、版本號與 `deleted_at`，其餘欄位在同一個交易裡清掉（下文〈Delete propagation 與 privacy〉的 Hard delete 那一列）。server 永久保留 tombstone 的代價是被刪掉的列一直佔著空間與索引，所以 server 會設一段保留期限，期限過了就清掉。server 清掉某個版本號以前的 tombstone 之後，接續標記停在那個版本號以前的裝置（長期離線的舊手機、很久沒開的平板）再拉取時，拿不到那段期間的刪除，本機會一直留著已經刪掉的列。

保留下限是 server 清 tombstone 時記下的、清到哪一個版本號為止，它標出增量拉取還能交出完整刪除紀錄的最舊位置。server 在拉取時先拿裝置的接續標記跟它比：接續標記比保留下限舊的，server 不回傳增量，改回應「需要全量重新同步」。公開的同步 API 用的是同一個形態，例如 Google Calendar API 的同步權杖（sync token）失效時回 `410 Gone`，要求用戶端改做一次完整同步（[Google Calendar API 的同步說明](https://developers.google.com/calendar/api/guides/sync)）。裝置收到之後走第一次同步的迴圈重新拉一次全部存活的列，拉完之後把本機有而 server 沒有回傳的列刪掉；本機 pending mutation 裡還沒送出的列要先送出或保留下來，否則重新同步會把使用者離線期間新增的資料一起刪掉。保留期限的長度要比裝置可能離線的最長時間長，期限越長，server 存的 tombstone 越多，全量重新同步發生的次數越少。

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

### Pending mutation 沒有 idempotency key，重送造成重複副作用

Pending mutation 沒有 idempotency key 的核心風險是重送造成重複副作用。網路 timeout 後 worker 重送，server 已經處理第一次請求，第二次又建立一筆資料或扣一次庫存。

修正方向是每個 mutation 生成 stable id，server 以 idempotency key 去重，local SQLite 保存 retry state 與 server ack。

### LWW 把衝突靜默變成使用者資料遺失

Last-write-wins 的核心風險是把衝突靜默變成資料遺失。Preference 類資料可接受；草稿、文件、表單、付款資料通常需要更清楚的 conflict handling。

修正方向是依資料價值分層。低價值設定用 LWW；高價值內容用 field merge、manual conflict 或 operation log。

### Delete 沒傳到離線裝置，重新上線時把已刪資料同步回來

Delete propagation 失敗的核心風險是 privacy / compliance 失效。使用者刪除 server 資料後，一台長期離線裝置重新上線又把舊資料同步回來。

修正方向是 tombstone + server authority。Server 要能拒絕過期 mutation，device 要能接收 delete tombstone 並 purge local state。

## 操作檢查清單

Local-first SQLite 設計要回答：

1. 哪些 table 是 local source of truth，哪些是 server replica。
2. Pending mutation 是否有 idempotency key 與 retry state。
3. 拉取的接續標記是不是由 server 在寫入交易裡指定、依提交順序遞增；接續標記有沒有帶主鍵當同值時的決勝欄位。
4. tombstone 的保留期限多長，接續標記比保留下限舊的裝置會不會被要求全量重新同步。
5. Conflict policy 是 LWW、field merge、manual merge 還是 operation log。
6. Delete 是否有 tombstone、ack 與 local purge。
7. Sync worker 是否有 backoff、dead-letter、reconciliation。
8. Device backup 是否會保存已刪資料。
9. Server 是否能拒絕過期 local write。

## 下一步路由

- 上游：[Mobile / Desktop Embedded Store](/backend/01-database/vendors/sqlite/mobile-desktop-embedded-store/)
- Sibling：[SQLite to D1 / Turso](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)、[D1 / Turso / libSQL Comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/)
- 卡片：[Idempotency](/backend/knowledge-cards/idempotency/)、[Eventual Consistency](/backend/knowledge-cards/eventual-consistency/)、[Stale Read](/backend/knowledge-cards/stale-read/)
- 跨模組：[Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)
