---
title: "SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍"
date: 2026-09-02
description: "未寫 ORDER BY 時列序隨索引與執行計畫變動的機制、ORDER BY 在求值順序的位置與可用別名，以及 NULL 在 SQLite、MySQL、PostgreSQL 與 DuckDB 排序中的預設位置與跨引擎寫法"
aliases: ["/sql/relations-have-no-order/"]
weight: 12
tags: ["sql", "order-by", "null", "query-plan", "semantic-model"]
---

這篇說明 SQL 查詢結果的列序來源與 `ORDER BY` 的作用範圍：先展示沒有 `ORDER BY` 時同一段查詢在建立索引前後如何回傳不同順序；說明 `ORDER BY` 在求值順序中的位置與引用別名的能力；最後比較 `NULL` 在 SQLite、MySQL、PostgreSQL 與 DuckDB 排序結果中的預設位置及跨引擎一致寫法。

本篇不處理以下相鄰主題：排序鍵存在同分列時分頁逐頁查詢造成的重複與遺漏，見 [SQL.12 分頁的排序鍵與接續標記：同分的列、全序與 OFFSET 的代價](/backend/01-database/sql/pagination-needs-a-total-order/)；連接條件放 `ON` 或 `WHERE` 的職責分工見 [SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/)，連接後的列數膨脹與空值比較見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)；視窗函數的 `OVER (ORDER BY ...)` 僅規定計算相鄰列的次序而不決定最終輸出列序，見 [SQL.10 分組與視窗函數：各自的產出、選用的依據與 LAG、LEAD 的相鄰列](/backend/01-database/sql/window-keeps-rows-grouping-collapses/) 的〈排序相鄰與需求要的相鄰：分區、排序鍵與距離條件〉一節。

在關聯模型裡，一份 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 是集合，集合成員本身不具先後順序。一段查詢產出的結果集天然沒有固定列序，實際回傳的排列方式取決於 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 採用的掃描或索引路徑。`ORDER BY` 是唯一替輸出規定列序的子句，且必須寫在最外層才生效；寫在衍生表或檢視表內部的 `ORDER BY` 可被引擎忽略：

```sql
-- MySQL 8.4
CREATE TABLE t (id INT PRIMARY KEY, k INT);
INSERT INTO t VALUES (1, 30), (2, 10), (3, 20);

SELECT group_concat(id) FROM (SELECT id FROM t ORDER BY k) d;
-- 1,2,3    主鍵序；衍生表裡的 ORDER BY k 被丟掉了
SELECT id FROM (SELECT id, k FROM t) d ORDER BY k;
-- 2、3、1  ORDER BY 寫在最外層才照 k 排
```

在 [Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/) 的各項規則中，輸出順序的限定範圍最小：模型只規定排序鍵值不同之列的先後，排序鍵值相同的列之間沒有規定次序。

以下範例沿用[SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/)的訂單表，將訂單 101 金額改為 700 並新增三張訂單，使五張訂單中有三張同為 500 元：

```sql
UPDATE 訂單 SET 金額 = 700 WHERE 訂單編號 = 101;
INSERT INTO 訂單 VALUES (103, 2, '2026-03-10', 500), (104, 2, '2026-03-11', 300),
                        (105, 3, '2026-03-12', 500);
-- 101 是 700 元，102、103、105 是 500 元，104 是 300 元
```

## 沒有 ORDER BY 時列序的來源

在未修改查詢文字的情況下，對同一批資料新建一個 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)，未寫 `ORDER BY` 的查詢便可能回傳完全不同的列序：

```sql
-- SQLite 3.51
SELECT 訂單編號 FROM 訂單 WHERE 金額 >= 300;
-- 101,102,103,104,105    計畫：SCAN 訂單

CREATE INDEX ix ON 訂單(金額);

SELECT 訂單編號 FROM 訂單 WHERE 金額 >= 300;
-- 104,102,103,105,101    計畫：SEARCH 訂單 USING INDEX ix (金額>?)
--   索引照金額排：300 的 104、500 的三張（102、103、105）、700 的 101
```

建索引前引擎掃描資料表，結果依儲存順序回傳；建索引後引擎改掃索引 `ix`，結果依金額由小到大回傳。由於查詢未指定 `ORDER BY`，這兩種順序都合乎標準。

在小資料量、執行計畫固定的開發環境中，沒有 `ORDER BY` 的查詢常每次回傳相同順序，容易被誤認為有保證；只要新增索引、資料量成長、統計資訊更新或更換引擎，列序就會在查詢文字完全未動的情況下改變。

## ORDER BY 在求值順序裡的位置與它用得到的別名

在求值順序裡，`ORDER BY` 排在 `SELECT` 之後，對已經算好的輸出列進行排序，因此可以直接引用 `SELECT` 建立的欄位別名：

```sql
SELECT 金額 * 2 AS 兩倍 FROM 訂單 ORDER BY 兩倍 DESC;
-- 三家都接受：1400、1000、1000、1000、600

SELECT 金額 * 2 AS 兩倍 FROM 訂單 WHERE 兩倍 > 1000;
-- PostgreSQL：column "兩倍" does not exist
-- MySQL：ERROR 1054 Unknown column '兩倍' in 'where clause'
-- SQLite：收下，回 1400
```

`WHERE` 執行於 `SELECT` 之前，此時欄位別名尚未建立，PostgreSQL 與 MySQL 因而拒絕。SQLite 接受在 `WHERE` 引用別名屬於引擎寬鬆，各子句求值順序與寬鬆放寬的完整說明見 [SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/)。

## NULL 在排序結果裡的位置與各家引擎的預設

當排序鍵允許 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)（例如選填的折扣金額或尚未完成的結案時間）時，因為 `NULL` 與任何值都無法比較大小，它排在結果集的前端或尾端由各家引擎自行定義。將訂單 103 的金額改為 `NULL` 並刪除訂單 105 後，在四家引擎測試升冪與降冪排序：

```sql
UPDATE 訂單 SET 金額 = NULL WHERE 訂單編號 = 103;
DELETE FROM 訂單 WHERE 訂單編號 = 105;
-- 101 是 700、102 是 500、103 是 NULL、104 是 300
```

| 引擎           | `ORDER BY 金額` | `ORDER BY 金額 DESC` |
| -------------- | --------------- | -------------------- |
| SQLite 3.51    | NULL 排最前     | NULL 排最後          |
| MySQL 8.4      | NULL 排最前     | NULL 排最後          |
| PostgreSQL 18  | NULL 排最後     | NULL 排最前          |
| DuckDB v0.10.3 | NULL 排最後     | NULL 排最後          |

這四家引擎的預設分為三種行為：SQLite 與 MySQL 把 `NULL` 視為比所有值小，PostgreSQL 把 `NULL` 視為比所有值大，DuckDB v0.10.3 則不論升冪或降冪預設一律 `NULLS LAST`。需要跨引擎固定空值位置時，必須在查詢中明確指定，而語法同樣分歧：

```sql
SELECT 訂單編號 FROM 訂單 ORDER BY 金額 NULLS LAST;
-- PostgreSQL 18、SQLite 3.51、DuckDB v0.10.3：104,102,101,103
-- MySQL 8.4：ERROR 1064 語法錯誤

-- 先排一個布林值：金額是 NULL 的列 (金額 IS NULL) 為真，排在為假的列之後
SELECT 訂單編號 FROM 訂單 ORDER BY (金額 IS NULL), 金額;
-- PostgreSQL 18、SQLite 3.51、MySQL 8.4、DuckDB v0.10.3：104,102,101,103
```

`NULL` 屬於無法比較大小的值；字串雖然可以比較大小，但大小寫是否視為相等、重音字元排在哪裡則取決於 collation 規則。[SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/) 比較了各引擎預設 collation 排序同一批字串的差異。
