---
title: "SQL Injection（SQL 注入）"
date: 2026-10-06
description: "看到程式把變數拼進 SQL 字串、或在審查資料存取的程式碼時，查它的值是用佔位符傳給資料庫，還是成了 SQL 文字的一部分"
weight: 457
tags: ["backend", "database", "security", "knowledge-card"]
---

SQL 注入（SQL injection）是使用者輸入的內容被資料庫當成 SQL 的一部分執行。成因只有一種：程式把值拼進 SQL 的字串裡，值裡的引號與關鍵字就和 SQL 的文字混在一起，資料庫分不出哪一段是程式寫的、哪一段是使用者送的。防範方式是用佔位符（placeholder）把值交給驅動處理，各語言的資料存取工具都有這個機制（各類工具的分層見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)），常和 [Prepared Statement](/backend/knowledge-cards/prepared-statement/) 一起出現。

## 概念位置

```go
// 值拼進字串：email 若是 ' OR '1'='1，WHERE 條件永遠成立，查詢回傳整張表
db.Query("SELECT * FROM customers WHERE email = '" + email + "'")

// 值用佔位符傳：email 的內容不論是什麼，都只會被當成一個字串值比對
db.Query("SELECT * FROM customers WHERE email = $1", email)
```

```php
// PHP（PDO）：同樣用佔位符，值在 execute 時另外送出
$stmt = $pdo->prepare('SELECT * FROM customers WHERE email = ?');
$stmt->execute([$email]);
```

```python
# Python（psycopg）：佔位符寫成 %s，值放在第二個參數，不用字串格式化
cur.execute("SELECT * FROM customers WHERE email = %s", (email,))
```

佔位符把值交給驅動處理：多數驅動把值和 SQL 分開送給資料庫（PostgreSQL 的擴充查詢協定、[Prepared Statement](/backend/knowledge-cards/prepared-statement/)），有的在用戶端依型別跳脫之後組進 SQL（PDO 對 MySQL 的預設，Laravel 則關掉了這個模擬；pgx 的 simple protocol 模式；Django 預設的用戶端綁定）；兩種做法下值都不會變成 SQL 的一部分。佔位符的寫法由驅動決定：PostgreSQL 的驅動用 `$1`、`$2`，MySQL 與 SQLite 的驅動多半用 `?`，PHP 的 PDO 與 Python 的部分驅動也接受 `:name` 這種具名寫法。ORM 與 Query Builder 從方法呼叫組出 SQL 時，同樣把值放進佔位符，所以值走條件方法的參數（GORM 或 Laravel 查詢建構器的 `where("email = ?", email)`）不會注入，把輸入拼進條件字串（`Where("email = '" + email + "'")`）一樣會注入；用它們的原始 SQL 入口（GORM 的 `Raw`、Laravel 的 `DB::raw`、Django 的 `raw()`）時，安全與否又回到程式有沒有用佔位符。

## 可觀察訊號與例子

- 程式碼裡 SQL 字串用 `+`、`fmt.Sprintf`、字串插值（`"... {$email}"`、`f"... {email}"`）組出，而且被組進去的是外部輸入。
- 佔位符只能代表**值**，不能代表表名、欄位名或 `ORDER BY` 的方向。這些位置要動態決定時，用程式裡的白名單對照（使用者送來 `name` 就換成欄位名 `name`，送來其他值就拒絕），不要把輸入直接放進去。
- 預存程序或資料庫函式裡用字串串接組出 `EXECUTE` 的 SQL，應用程式端用了佔位符也擋不住；PostgreSQL 改用 `EXECUTE ... USING` 傳值，識別字用 `format('%I', ...)`。
- 錯誤訊息或資料庫的語句記錄裡出現語法錯誤，而觸發它的輸入含有引號，是有地方在拼字串的訊號。

## 設計責任

審查資料存取的程式碼時，找出每一個 SQL 字串是怎麼組出來的：值一律走佔位符；必須動態的識別字一律走白名單。注入的後果不限於讀出別人的資料，也包括改寫或刪除整張表，越權查詢與資料外洩路徑的判讀見 [1.5 攻擊者視角（紅隊）：資料層弱點判讀](/backend/01-database/red-team-data-layer/)。
