---
title: "SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表"
date: 2026-09-24
description: "SQL 各篇共用的顧客、訂單與評價表建表語句與初始資料，以及各篇輸出使用的引擎版本、錯誤訊息、列序與篇內資料增刪的閱讀約定"
aliases: ["/sql/sample-bookstore-database/"]
weight: 25
tags: ["sql", "sample-data", "reference"]
---

這篇提供 SQL 分類多數文章共用的範例資料庫結構與初始資料（一家小書店的顧客、訂單與評價三張資料表），並說明各篇實測採用的資料庫引擎版本，以及閱讀錯誤訊息、輸出列序與篇內資料變動時的約定。涉及執行代價與大量資料的篇章會另行建立測試表，並於該篇內標明。

## 建表語句與初始資料

```sql
CREATE TABLE 顧客 (顧客編號 INT, 姓名 TEXT);
CREATE TABLE 訂單 (訂單編號 INT, 顧客編號 INT, 下單日 TEXT, 金額 INT);
CREATE TABLE 評價 (評價編號 INT, 訂單編號 INT, 星等 INT);

INSERT INTO 顧客 VALUES (1,'佳穎'), (2,'宗翰'), (3,'雅文');
INSERT INTO 訂單 VALUES (101,1,'2026-03-02',300), (102,1,'2026-03-09',500);
INSERT INTO 評價 VALUES (9001,101,5);
```

三位顧客中只有佳穎下過訂單，她的兩張訂單中只有第一張有評價。這些缺漏刻意保留，讓外連接、空值比較與 `ON`／`WHERE` 條件位置的差別能在小資料上直接顯現。

`RIGHT JOIN` 與 `FULL OUTER JOIN` 屬於 SQLite 較新版本才加入的語法，舊版執行時會回報語法錯誤；遇到時可執行 `sqlite3 --version` 確認本機 SQLite 版本。

## 各篇輸出所用的引擎版本與閱讀輸出的約定

各篇展示的輸出皆經實際執行取得，多數跑在 SQLite 3.51。[SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/) 整篇使用 PostgreSQL 18；跨引擎對照的篇章另搭配 MySQL 8.4 與 DuckDB v0.10.3，部分篇章與知識卡另使用 SQLite 3.53.0／3.43.2、PostgreSQL 16 或 DuckDB 1.5.5，凡涉及引擎行為差異或採用其他版本處皆於該處標明引擎名稱與版本。

**錯誤訊息**：各家引擎在不同版本間可能調整錯誤訊息措辭。各篇引用的錯誤字串作為對照，判讀重點在於引擎拒絕該語法或操作的原因，而非逐字比對措辭。

**列序**：各篇列出的結果集為了便於比對而採固定順序呈現；未寫 `ORDER BY` 的查詢在實際執行時沒有列序保證（詳見 [SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍](/backend/01-database/sql/relations-have-no-order/)）。

**篇內資料增刪**：部分文章會在共用資料上新增或修改若干列以展示特定效果，這類變動僅在該篇內部有效；切換至另一篇文章時，資料狀態回到本頁最上方的初始建表與資料內容。
