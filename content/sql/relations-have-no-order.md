---
title: "1.11 關係沒有順序，只有 ORDER BY 加得回來"
date: 2026-09-02
description: "同一段查詢在建索引前後回不同順序的機制、ORDER BY 在求值順序的位置，以及空值落在哪一端各家的差別"
weight: 11
tags: ["sql", "order-by", "null", "query-plan", "semantic-model"]
---

一份 [relation](/sql/knowledge-cards/relation/) 是集合，而集合的成員沒有先後。所以一段查詢算出來的那份關係本身不帶順序，回到手上的那一批列排成什麼樣，是[執行計畫](/sql/knowledge-cards/query-plan/)走到最後剛好留下的形狀。`ORDER BY` 是把順序加回去的那個子句，也是唯一的一個——而它要寫在**最外層**才算數。寫在衍生表或視圖裡面的 `ORDER BY` 引擎可以丟掉：MySQL 8.4 上 `SELECT group_concat(id) FROM (SELECT id FROM t ORDER BY k) d` 回的是主鍵序而不是 `k` 的序。

這個語言用一套規則決定哪些列會出現在結果裡（那套規則叫[語意模型](/sql/knowledge-cards/semantic-model/)），而輸出的順序是它管得最少的一項：**規則只到「排序鍵分得出高下」為止，分不出高下的那些它沒有規定**。

本篇交代順序從哪裡來、`ORDER BY` 看得到什麼、以及比不出大小的值落在哪一端。**規則沒有規定的那一半在什麼時候變成錯誤，在 [1.12](/sql/pagination-needs-a-total-order/)**——分頁是它最常現形的地方。

本篇的查詢跑在[共用資料庫](/sql/#各篇共用的範例資料庫)的訂單表上，並把訂單加到五張，其中三張同樣是 500 元：101 是 700 元、102 與 103 是 500 元、104 是 300 元、105 是 500 元。

## 沒有 ORDER BY 的時候，順序跟著計畫走

同一段查詢，同一批資料，中間只多建了一個索引：

```text
-- SQLite 3.51
SELECT 訂單編號 FROM 訂單 WHERE 金額 >= 300;

建索引之前   101,102,103,104,105     計畫：SCAN 訂單
建索引之後   104,102,103,105,101     計畫：SEARCH 訂單 USING INDEX ix (金額>?)
```

查詢的文字一個字都沒改，回來的順序整個換掉了。第一種照資料存放的先後走，第二種照索引上的先後走——**兩種都正確**，因為那份關係本來就沒有規定過順序。

這件事在開發時多半看不見。一張小表、一種計畫，看到的順序穩定得像是有保證，而讓它變動的條件（建了索引、資料長大、統計更新、換一家引擎）沒有一項在查詢的文字裡。

## ORDER BY 在求值順序的最後一段，所以它看得到輸出欄位

`ORDER BY` 排的是 `SELECT` 已經算完的那份結果，所以 `SELECT` 裡取的別名它用得到：

```sql
SELECT 金額 * 2 AS 兩倍 FROM 訂單 ORDER BY 兩倍 DESC;   -- 三家都接受
SELECT 金額 * 2 AS 兩倍 FROM 訂單 WHERE 兩倍 > 1000;    -- PostgreSQL 與 MySQL 拒絕
```

`WHERE` 那一步發生在算出 `兩倍` 之前，所以那個名字在那裡還不存在——PostgreSQL 回 `column "兩倍" does not exist`，MySQL 回 `ERROR 1054 Unknown column '兩倍' in 'where clause'`。SQLite 收下同一段並回答 1400，這是它的寬鬆度而不是標準行為（求值順序的完整推導與這條寬鬆度的其他實例在 [1.2](/sql/clause-evaluation-order/)）。

## NULL 排在哪一端，三家給兩種答案

排序鍵含[空值](/sql/knowledge-cards/null/)的時候，`NULL` 與任何值都比不出大小，所以它落在哪一端由引擎自己規定。會同時是排序鍵又可能為空的欄位不少——選填的折扣金額、還沒完成的那些列的完成時間，都是拿來排序的常見對象。同一批四列（700、500、NULL、300）：

| 引擎           | `ORDER BY 金額` | `ORDER BY 金額 DESC` |
| -------------- | --------------- | -------------------- |
| SQLite 3.51    | NULL 排最前     | NULL 排最後          |
| MySQL 8.4      | NULL 排最前     | NULL 排最後          |
| PostgreSQL 18  | NULL 排最後     | NULL 排最前          |
| DuckDB v0.10.3 | NULL 排最後     | NULL 排最前          |

兩種規定各自自洽：SQLite 與 MySQL 把 `NULL` 當成比任何值都小，PostgreSQL 與 DuckDB 當成比任何值都大。要跨引擎一致就得寫出來，而寫法本身也分兩家——`ORDER BY 金額 NULLS LAST` 在 PostgreSQL 18 與 SQLite 3.51 上直接支援，MySQL 8.4 回 `ERROR 1064` 語法錯誤。三家都收的寫法是先排一個布林值：`ORDER BY (金額 IS NULL), 金額`，實測三家回的都是 104,102,101,103。

## 換掉其中一項就走到另一篇

本篇底下有三樣可以各自換掉：順序寫不寫出來、排序鍵分不分得出高下、以及鍵的型別。

**把「規則沒有規定的那一半」從無害換成錯誤**：整批看的時候同分的列換位置沒有後果，而每一頁各查一次的時候它變成重複與遺漏。[1.12 分頁要一個全序](/sql/pagination-needs-a-total-order/) 寫那個機制、補到兩兩可分的判準，以及把游標從位置換成值的兩種寫法。

**把「哪些列出現」換成「它們排成什麼樣」的反向**：本篇處理輸出的形狀，而哪些列會進到這份結果由條件與連接決定。[1.5 ON 描述關係、WHERE 篩選結果](/sql/on-describes-where-filters/) 寫條件擺哪一邊決定留下哪些列，[1.6 連接產出的是新的關係](/sql/join-changes-rows-and-nulls/) 寫連接怎麼改變列數。

**把「整批的順序」換成「每一列與它鄰居的關係」**：視窗函數的 `OVER (ORDER BY ...)` 與這裡的 `ORDER BY` 是兩個不同的順序——一個決定計算時誰算相鄰，一個決定輸出怎麼排，兩者可以不同。[1.10 分組把列收掉，視窗函數把列留著](/sql/window-keeps-rows-grouping-collapses/) 的「相鄰的是什麼」一節寫計算時誰算相鄰的那一種。

**把排序鍵從數字換成字串**：那時「誰在前面」由比較規則決定，而各家的預設不同，同一批名字排出來的順序也不同。[1.15 字串的相等、大小與索引可用性都由 collation 決定](/sql/string-comparison-and-collation/) 寫這條規則住在哪裡。
