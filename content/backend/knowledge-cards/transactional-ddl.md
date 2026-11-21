---
title: "Transactional DDL（交易性 DDL）"
date: 2026-11-21
description: "migration 跑到一半失敗、要判斷資料庫停在哪個狀態，或選資料庫與 migration 工具時，查 CREATE、ALTER、DROP 能不能跟一般寫入一樣隨交易回滾，以及 PostgreSQL 與 MySQL 的差別"
weight: 509
tags: ["backend", "database", "postgresql", "mysql", "transaction", "schema migration", "knowledge-card"]
---

Transactional DDL（交易性 DDL）指資料庫允許 `CREATE`、`ALTER`、`DROP` 這類 [DDL](/backend/01-database/sql/knowledge-cards/ddl-dml/) 跟一般的寫入放在同一個 [Transaction](/backend/knowledge-cards/transaction/) 裡：交易提交時一起生效，交易回滾（transaction rollback，`ROLLBACK`）時一起撤銷。PostgreSQL 支援，所以一份 [Schema Migration](/backend/knowledge-cards/schema-migration/) 在第三句失敗時，前兩句的改名與加欄也隨交易回滾，資料庫停在套用之前的狀態；MySQL 不支援，DDL 執行時會先把目前的交易提交（implicit commit），失敗時已經執行的那幾句留在資料庫裡。

## 跟其他概念的關係

Transactional DDL 是資料庫的能力，migration 工具決定要不要用它：goose、Flyway、Django 預設把每一份 migration 包成一個交易，Alembic 預設把一次 `upgrade` 的整批包成一個交易，在 PostgreSQL 上因此得到「失敗就整份隨交易回滾、歷史表也不記錄」。同一個交易持有的鎖到提交才放掉，DDL 拿的強鎖會讓 [Lock Queue](/backend/knowledge-cards/lock-queue/) 排得更久，所以交易包得越大，擋住讀寫的時間越長。PostgreSQL 也有不能放進交易的語句，`CREATE INDEX CONCURRENTLY` 是最常見的一個，那一份 migration 要讓工具不包交易，失敗時的行為就跟 MySQL 一樣。

## 可觀察訊號與例子

實測 PostgreSQL 17 上一份先改名、後一句失敗的 migration，Alembic、goose、Django 5.2、Flyway 13.13.0 都把改名一起隨交易回滾，歷史表沒有這一筆；Alembic 與 goose 那一次失敗的是把欄位縮成放不下既有資料的長度，PostgreSQL 回 `value too long for type character varying(20)`。不包交易的 goose migration 建兩個 index、第二句失敗時，第一個 index 已經建好、歷史表沒有記錄，修正之後重跑，第一句反而以 `relation ... already exists` 失敗；步驟在 [goose 管理 PostgreSQL migration 的實測紀錄](/programming/go/basic/10-database-access/hands-on/goose-migration-lab/)。MySQL 上的訊號是 migration 失敗之後，部分欄位或表已經存在，而工具的歷史表沒有這一份。

## 判斷條件與後果

資料庫支援 transactional DDL、而且那一份 migration 包在交易裡時，失敗之後修正檔案再重跑即可，不必先查資料庫做到哪一句。不支援（MySQL），或那一份 migration 不包交易（`CONCURRENTLY`）時，失敗會留下部分變更：重跑前要人查出實際狀態、手動復原或補完，再修正工具的歷史紀錄（Flyway 的 `repair`、golang-migrate 的 `force`）；在應用程式啟動時套用的服務，這段期間每次重啟都卡在同一份失敗的 migration 上。所以不包交易的 migration 一份只放一句，或每一句寫成重跑也成立的形式（`IF NOT EXISTS`）。兩種套用時機在失敗時的差別寫在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/)〈套用的時機〉。
