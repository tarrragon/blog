---
title: "Connection Leak（連線洩漏）"
date: 2026-10-06
description: "請求越來越慢、最後在等連線時逾時，而資料庫本身負載不高，或連線池使用中的數量一直停在上限時，查哪一段程式借了連線沒有還"
weight: 460
tags: ["backend", "database", "connection-pool", "knowledge-card"]
---

連線洩漏（connection leak）是程式向 [Connection Pool](/backend/knowledge-cards/connection-pool/) 借了一條連線，用完卻沒有還回池裡。那條連線在池的帳上一直是「使用中」，洩漏累積到池的上限之後，之後每一個要用資料庫的請求都排隊等連線，等到逾時為止。資料庫那一端這時負載多半很低：連線開著，上面沒有在執行的查詢。和它症狀相同、成因不同的是連線被長時間合法持有，最常見的是交易開著時去呼叫外部服務（長交易佔住連線的成本見 [Transaction](/backend/knowledge-cards/transaction/)，外部呼叫要不要放進交易見 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/)）。

## 概念位置

連線在程式碼上不一定以「連線」的樣子出現，查詢結果的讀取物件（[Cursor](/backend/knowledge-cards/cursor/)）與交易（[Transaction](/backend/knowledge-cards/transaction/)）都各自佔著一條，所以借出的位置常常不明顯。各語言最常見的借出點：

- **Go 的 `database/sql`**：查詢回傳的 `*sql.Rows` 在 `Close` 或讀到最後一列之前佔著一條連線；`*sql.Tx` 在 `Commit` 或 `Rollback` 之前佔著一條連線。讀到一半就 `return`、又沒有 `defer rows.Close()` 是最常見的洩漏（實測見 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/)〈查詢結果讀取物件（*sql.Rows）的關閉與連線洩漏〉）。`QueryRowContext` 回傳的 `*sql.Row` 要呼叫 `Scan` 才歸還連線，`db.Conn(ctx)` 借出的專用連線要 `Close`。pgx 的 `pgxpool` 用 `Acquire` 明確借出時，要對應一次 `Release`。
- **Python**：`psycopg_pool` 的 `getconn()` 要對應 `putconn()`，SQLAlchemy 的 `engine.connect()` 與 `Session` 要關閉；寫成 `with` 區塊時，區塊結束就歸還，洩漏多半出在沒有用 `with` 的那幾處。
- **PHP-FPM**：沒有開持久連線（`PDO::ATTR_PERSISTENT`）時，請求結束時 PHP 釋放這個請求的所有資源，連線跟著關閉，所以單一請求內的洩漏不會跨請求累積；改成常駐 worker（Laravel Octane、FrankenPHP 的 worker 模式），以及本來就常駐的佇列 worker（`php artisan queue:work`）之後，跨請求或跨工作留著的物件就可能一直握著連線；Python 的 Celery worker 同理。

## 可觀察訊號與例子

- **池的指標**：使用中的連線數一直貼著上限、等待連線的次數持續上升，而查詢的執行時間沒有變長。Go 的 `db.Stats()` 是 `InUse` 與 `WaitCount`；SQLAlchemy 在等不到連線時拋出 `QueuePool limit of size 5 overflow 10 reached, connection timed out` 這類錯誤。
- **資料庫端**：PostgreSQL 的 `pg_stat_activity` 裡，來自應用程式的連線長時間停在 `idle`（池裡正常閒置的連線也是 `idle`，所以要對照池的帳：池說使用中、資料庫說閒置的那些才是借出後沒在用的）或 `idle in transaction`（交易開著沒有結束）。寫過資料或跑在 repeatable read 以上的 `idle in transaction` 另外會擋住 VACUUM 清理舊版本的資料列，`idle_in_transaction_session_timeout` 可以讓 PostgreSQL 主動切斷這種連線（擋住 VACUUM 的機制見 [PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價](/backend/01-database/vendors/postgresql/mvcc-lock-model/)）。
- **找出是哪一段程式**：`pg_stat_activity` 的 `query` 欄是那條連線最後執行的語句，`application_name`（連線字串可以設定）標出是哪個服務；停在 `idle in transaction` 或池說使用中的連線，最後一句 SQL 通常就指向借出連線的那段程式。
- **只在流量高或長時間運行之後才出現**：池的上限越大，洩漏要累積越久才浮現。本機開發把池上限設成 1 或 2，同樣的洩漏在第二個查詢就卡住，最容易重現。

## 設計責任

借出與歸還寫在同一個作用域裡，讓語言的機制保證歸還：Go 在取得 `*sql.Rows` 或 `*sql.Tx` 的下一行寫 `defer Close()` 或 `defer Rollback()`，Python 用 `with`。監控上要能看到池的使用中、閒置與等待次數；測試裡可以在每個測試結束時檢查池的使用中連線數回到 0，讓洩漏在測試階段就失敗。Java 的 HikariCP 這類連線池內建洩漏偵測（連線借出超過設定時間就記錄借出位置的 stack trace），Go 的 `database/sql` 沒有，要靠池的使用中連線數、等待次數，以及測試結束時的連線數檢查。
