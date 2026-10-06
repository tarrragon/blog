---
title: "Prepared Statement（預先解析的查詢）"
date: 2026-10-06
description: "在資料庫的語句記錄裡看到 stmtcache_、pdo_stmt_ 這類具名的查詢被重複執行，或應用程式接上 PgBouncer 交易模式後出現 prepared statement already exists、does not exist 的錯誤時，查它在哪一條連線上建立、存在多久"
weight: 458
tags: ["backend", "database", "postgresql", "knowledge-card"]
---

預先解析的查詢（prepared statement）是先把一段帶佔位符的 SQL 送給資料庫解析與規劃，資料庫給它一個名字存起來，之後每次只送名字與參數值就能執行。其他中文資料常寫作預備語句或預處理語句。省下的是重複解析同一段 SQL 的成本，執行計畫是否重用另由資料庫的計畫快取決定（見下方〈可觀察訊號與例子〉的通用計畫）；佔位符讓值與 SQL 分開送，也是防 [SQL 注入](/backend/knowledge-cards/sql-injection/) 的機制之一。它的生命週期綁在建立它的那一條資料庫連線上，所以和 [Connection Pool](/backend/knowledge-cards/connection-pool/)、[Connection Pooler](/backend/knowledge-cards/connection-pooler/) 的行為直接相關。

## 概念位置

```sql
PREPARE orders_by_customer (bigint) AS
  SELECT id, amount FROM orders WHERE customer_id = $1;

EXECUTE orders_by_customer(1);
EXECUTE orders_by_customer(2);
```

應用程式多半不直接寫 `PREPARE`，而是由驅動代勞，而驅動的連線來自 [Connection Pool](/backend/knowledge-cards/connection-pool/)：有的驅動每次執行都先解析再丟棄，有的會在每條連線上快取執行過的查詢（Go 的 pgx 預設如此，在 PostgreSQL 的語句記錄（`log_statement`）裡會看到以 `stmtcache_` 開頭的名字被重複執行，見 [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/)）。

## 可觀察訊號與例子

- **它只存在於一條連線上**：連線關閉，名字就消失；另一條連線上沒有這個名字。
- **和交易模式的連線池代理衝突**：PgBouncer 這類代理在交易模式（transaction pooling）下，應用程式連到代理的那條連線不變，而代理每個交易都可能從它對資料庫的連線裡挑另一條，名字就對不上：同一個名字可能已經被另一條應用程式連線建在那條資料庫連線上（實測 pgx 遇到的是 `prepared statement "stmtcache_…" already exists (SQLSTATE 42P05)`），也可能在那條資料庫連線上根本不存在。處理方式是讓代理追蹤這些名字（PgBouncer 1.21 起支援，`max_prepared_statements` 要設成非 0；1.24 起預設是 200，也就是預設開啟），或讓驅動不留下具名的預先解析查詢（見 [Transaction Pooling](/backend/knowledge-cards/transaction-pooling/)）。
- **計畫可能被重用**：PostgreSQL 對同一個預先解析的查詢執行幾次之後，可能改用不看參數值的通用計畫（generic plan）；資料分布很不平均時，某些參數值會因此走到較差的計畫。`plan_cache_mode` 設定控制這個行為。

## 設計責任

用驅動的預設行為之前，先確認兩件事：驅動會不會在連線上快取預先解析的查詢，以及應用程式與資料庫之間有沒有交易模式、而且沒有追蹤預先解析查詢的連線池代理（PgBouncer 1.21 到 1.23 的預設，或 `max_prepared_statements` 設成 0）。兩者同時成立時要擇一調整，否則錯誤只在流量讓同一條應用程式連線跨到不同資料庫連線時才出現，本機開發與低流量測試都重現不了。
