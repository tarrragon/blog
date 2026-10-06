---
title: "1.16 Schema 設計決定的查詢代價：可空性、排序鍵唯一性、表寬、一對多的切法、比較規則與外鍵執法"
date: 2026-09-22
description: "建表時每一個決定有哪些選法、選了之後查詢要多做什麼、代價在什麼條件下才浮現、改回來要付的遷移成本，以及設計當下就能問的問題；輸出為 SQLite 與 PostgreSQL 的實測"
weight: 16
tags: ["backend", "database", "schema", "query", "design"]
---

這一篇走建表時要下的六個 schema 決定：欄位允不允許為空、排序鍵唯不唯一、長欄位跟其餘欄位放不放同一張表、常一起取的資料切在幾張表、字串的比較規則寫在哪一層、宣告的外鍵生不生效。範圍從 `CREATE TABLE` 的內容開始，到那些決定在往後的查詢上要付什麼為止。

這幾個決定寫進 `CREATE TABLE` 是同一個動作，花同樣的時間，跑起來同樣成功，而**設計當下看不出哪一種選法比較貴**。每一個決定的兩種選法在設計當下都成立，而其中一種把代價轉給往後的查詢，由每一次查詢分期付。

範圍：這裡談決定與它的查詢代價。那些查詢本身怎麼寫在 [SQL：這個語言為什麼長這樣](/backend/01-database/sql/)；已經寫成那樣的查詢怎麼修在 [1.13 應用層查詢反模式](/backend/01-database/query-anti-patterns/)；改 schema 的動作怎麼分段執行在 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)。

本篇的輸出都是實際跑出來的，每一段標明引擎。多數量測在 SQLite 3.51.0；collation 那一節整節在 PostgreSQL 18.6（索引能不能用要看計畫，而 SQLite 沒有對應的形態），外鍵那一節兩家並排。

## 欄位的可空性

**要決定的**：訂單有一欄「優惠券編號」，而不是每張訂單都用了優惠券。

**兩條路**。允許為空——沒用優惠券的訂單這一欄留空，讀起來就是事實本身的形狀。或者不允許為空，替「沒有用優惠券」給一個實際的值（一個保留編號，或者把「用了哪一張券」整個搬到另一張表，有券的訂單才在那張表裡有一列）。

設計當下允許為空明顯自然，給一個實際的值看起來像在替一個不存在的東西發明代號。

**選了允許為空之後，查詢要多做什麼**。三張優惠券裡「生日」從來沒有被用過，三張訂單裡有一張沒有用券：

```sql
-- SQLite 3.51.0
-- 各節的表名重複，照順序跑要先清掉上一節的（SQLite 的 DROP 一次只收一張表）
DROP TABLE IF EXISTS 優惠券;
DROP TABLE IF EXISTS 訂單;
CREATE TABLE 優惠券 (優惠券編號 INTEGER PRIMARY KEY, 名稱 TEXT);
INSERT INTO 優惠券 VALUES (9001,'新客'),(9002,'週年'),(9003,'生日');

CREATE TABLE 訂單 (訂單編號 INTEGER PRIMARY KEY, 顧客編號 INT, 優惠券編號 INT, 金額 INT);
INSERT INTO 訂單 VALUES (101,1,9001,300),(102,1,NULL,500),(103,2,9002,200);
```

問「哪幾張優惠券從來沒有被用過」：

```sql
-- NOT IN
SELECT 名稱 FROM 優惠券 WHERE 優惠券編號 NOT IN (SELECT 優惠券編號 FROM 訂單);

-- NOT EXISTS，問的是同一件事
SELECT 名稱 FROM 優惠券
WHERE NOT EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.優惠券編號 = 優惠券.優惠券編號);
```

```text
NOT IN      0 列，沒有任何錯誤訊息
NOT EXISTS  生日
```

訂單 102 的空值換成一個實際的值之後，`NOT IN` 也回「生日」：

```sql
UPDATE 訂單 SET 優惠券編號 = 0 WHERE 訂單編號 = 102;
SELECT 名稱 FROM 優惠券 WHERE 優惠券編號 NOT IN (SELECT 優惠券編號 FROM 訂單);
-- 生日
```

分岔的機制是三值邏輯。`NOT IN` 拿外層的值跟子查詢交回的每一個值各比一次「不等於」，再用 `AND` 串起來；其中一項拿 `NULL` 去比，那一項的真值是未知，整串因此不會判成真（完整推導在 [SQL.6 連接之後的列數與空缺](/backend/01-database/sql/join-changes-rows-and-nulls/)）。以「生日」那一列為例：

```sql
-- 子查詢交回 9001、NULL、9002，對「生日」（9003）展開
SELECT 9003 NOT IN (9001, NULL, 9002);                     -- NULL（未知）
SELECT 9003 <> 9001 AND 9003 <> NULL AND 9003 <> 9002;     -- NULL：真 AND 未知 AND 真
```

`WHERE` 只留判成真的列，所以「生日」被濾掉。這裡要看的是**那個空值是 schema 允許它存在的**，而查詢沒有寫錯。

`NOT IN` 的分岔之外，這一欄允許為空還讓每一段碰到它的查詢多處理幾件事，不只「哪幾張券沒被用過」這一題：

```sql
-- 資料是建表時那一份：訂單 102 的優惠券編號是 NULL
SELECT count(優惠券編號), count(*) FROM 訂單;
-- 2|3：count(欄位) 只數有值的列，count(*) 數全部列，兩者從此是兩個數字

SELECT count(*) FROM 訂單 WHERE 優惠券編號 = NULL;
-- 0：拿 NULL 比等號判成未知，不報錯；要找空值得寫 優惠券編號 IS NULL（回 1）

SELECT 訂單編號 FROM 訂單 ORDER BY 優惠券編號;
-- 102, 101, 103：SQLite 升冪時把 NULL 排最前
```

升冪排序時空值落在哪一端由引擎自己規定，SQLite 與 MySQL 排最前、PostgreSQL 與 DuckDB 排最後；降冪時 SQLite、MySQL、PostgreSQL 都翻到另一端，DuckDB 仍排最後（[SQL.11 查詢結果的列序](/backend/01-database/sql/relations-have-no-order/) 的四家對照）。**每一條都是這一欄允許為空之後，往後每一段碰到它的查詢都要處理的事。**

**代價在什麼條件下浮現**。第一張沒有用優惠券的訂單被寫進來的那一刻——不是 schema 變更的時刻。在那之前這一欄裡沒有空值，`NOT IN` 與 `NOT EXISTS` 回同一個答案，測試會過，而 schema 早就已經是現在這個樣子了。

**改回來要付什麼**。把欄位改成 `NOT NULL` 要先處理存量的空值，也就是替每一列決定它該填什麼——而那個決定當初沒有做，所以現在多半找不到依據。這條路在 [backend 1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) 裡是 `Type G：加 NOT NULL constraint`，三步：**先讓應用端所有實例停止寫入空值**（少了這一步，補完值之後新的空值又進來）、再回填既有的空值、最後才加約束。`CHECK` 與外鍵走的是另一型（`Type I`）的兩段式，那一型才用 `NOT VALID` 加 `VALIDATE`。

**所以設計當下要問的是**：這一欄的空值，代表「還不知道」、「不適用」、還是「確定沒有」。三種是不同的事實，而 `NULL` 只有一個，把它們併成同一個值之後，往後每一段查詢都要從別的欄位去猜是哪一種。分得開的那幾種，各自給一個實際的值或各自一張表。

## 排序鍵的唯一性

**要決定的**：訂單列表要按下單日排序給使用者翻頁。下單日這一欄唯不唯一。

**兩條路**。就讓它不唯一——同一天本來就可以下好幾張單，這是事實。或者把「拿來排序的鍵」與「記錄事實的欄位」當成兩件事，排序時另外補一個一定分得出高下的欄位。

設計當下只按下單日排序根本不像一個決定，因為它不是在 `CREATE TABLE` 裡寫的東西——**它是預設，而預設不會被拿出來討論**。

**只按下單日排序之後，查詢要多做什麼**。六張訂單，其中四張同一天：

```sql
-- SQLite 3.51.0
-- 各節的表名重複，照順序跑要先清掉上一節的（SQLite 的 DROP 一次只收一張表）
DROP TABLE IF EXISTS 訂單;
CREATE TABLE 訂單 (訂單編號 INTEGER PRIMARY KEY, 下單日 TEXT, 金額 INT);
INSERT INTO 訂單 VALUES
 (101,'2026-03-02',300),(102,'2026-03-02',500),(103,'2026-03-02',200),
 (104,'2026-03-02',450),(105,'2026-03-05',700),(106,'2026-03-09',150);
```

每頁兩列翻三頁。使用者翻到第一頁之後、翻第二頁之前，有人替這張表加了一個索引：

```sql
-- 第 1 頁（此時還沒有索引）
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日 LIMIT 2 OFFSET 0;

-- 有人在這個時間點建了索引。第二欄 金額 不是裝飾——
-- 它決定同一天那四張訂單在索引上的先後，而掃全表時的先後由存放順序決定，
-- 兩者不同才看得到下面的錯位。只建 (下單日) 的話兩種順序剛好一致，什麼事都不會發生。
CREATE INDEX ix_日金 ON 訂單(下單日, 金額);

-- 第 2、3 頁（此時有索引了）
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日 LIMIT 2 OFFSET 2;
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日 LIMIT 2 OFFSET 4;
```

```text
第 1 頁   101, 102
第 2 頁   104, 102
第 3 頁   105, 106

使用者拿到的整份清單：101, 102, 104, 102, 105, 106
```

**102 出現兩次，而 103 一次都沒有出現。** 兩次查詢都沒有報錯，兩次的結果也都正確——四張同一天的訂單之間，`ORDER BY 下單日` 沒有規定誰在前面，所以掃全表時照存放順序、走索引時照索引順序，兩種都合法（機制在 [SQL.11 查詢結果的列序](/backend/01-database/sql/relations-have-no-order/)）。

**這個示範要成立，索引的第二欄是必要的。** 索引只建下單日一欄時，同一份資料的第 2 頁不重複也不遺漏：

```sql
DROP INDEX ix_日金;
CREATE INDEX ix_日 ON 訂單(下單日);
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日 LIMIT 2 OFFSET 2;
-- 103, 104：SQLite 的單欄索引以 rowid 決勝，剛好與掃全表的順序一致
```

**這件事本身就是這一節的結論**：並列的列由什麼決勝沒有規定，所以它可以剛好一致、也可以剛好不一致，而查詢的文字對這件事完全沉默。

補一個決勝鍵之後，同一組操作在有索引與沒索引底下給同一份清單：

```sql
-- 沒有索引、只有 ix_日金、只有 ix_日 三種狀態下，三頁都回同一份清單
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日, 訂單編號 LIMIT 2 OFFSET 0;
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日, 訂單編號 LIMIT 2 OFFSET 2;
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日, 訂單編號 LIMIT 2 OFFSET 4;
```

```text
第 1 頁   101, 102
第 2 頁   103, 104
第 3 頁   105, 106
```

**代價在什麼條件下浮現**。並列造成的那一種要三件事同時成立：排序鍵上有並列的列、同一次翻頁跨過了計畫改變的時刻、而且剛好有人在看。開發時資料少、只有一種計畫，順序穩定得像是有保證，而讓它變動的條件（建了索引、資料長大、統計更新、換一台複本）沒有一項在查詢的文字裡。

**而補決勝鍵只治好並列那一種。** 同一組資料、不建任何索引、計畫全程不變，只要在翻頁中間寫進一張排在接續標記（cursor）前面的訂單，補了決勝鍵的版本照樣重複與遺漏：

```sql
-- 回到建表時的六張訂單，拿掉前面建的索引
DROP INDEX IF EXISTS ix_日金;
DROP INDEX IF EXISTS ix_日;
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日, 訂單編號 LIMIT 2 OFFSET 0;   -- 第 1 頁：101, 102

INSERT INTO 訂單 VALUES (107,'2026-03-01',100);   -- 翻頁途中寫進一張排在最前面的訂單

SELECT 訂單編號 FROM 訂單 ORDER BY 下單日, 訂單編號 LIMIT 2 OFFSET 2;   -- 第 2 頁：102, 103，102 重複
SELECT 訂單編號 FROM 訂單 ORDER BY 下單日, 訂單編號 LIMIT 2 OFFSET 4;   -- 第 3 頁：104, 105，106 從未出現
```

`OFFSET` 數的是位置，而位置會被排在接續標記前面的寫入改變——翻頁途中的寫入造成的錯位不需要並列、不需要計畫改變，只需要一邊翻頁一邊有人在寫。要免疫於它，接續標記得從位置換成值（[SQL.12 分頁的排序鍵與接續標記](/backend/01-database/sql/pagination-needs-a-total-order/) 寫兩種接續標記的取捨，並說明補唯一鍵治好了哪一種、治不好哪一種）。**本節的決定只治得好並列造成的重複與遺漏**；翻頁途中的寫入造成的那一種要靠應用層把接續標記從位置換成值，schema 管不到。

排序鍵不唯一的另一個代價落在「拿前一筆比較」那一族問題上：排序鍵有並列時「前一列」是哪一列沒有定義，`LAG` 與自連接都受影響（[SQL.10 分組與視窗函數：各自的產出、選用的依據與 LAG、LEAD 的相鄰列](/backend/01-database/sql/window-keeps-rows-grouping-collapses/)）。

**改回來要付什麼**。補決勝鍵只要改查詢，不用動 schema——這是六個決定裡最便宜的一個。真正的成本在**找出全部要改的地方**：每一段有 `ORDER BY` 加 `LIMIT` 的查詢都要查一次它的排序鍵唯不唯一，而那些查詢散在整個程式裡。

**所以設計當下要問的是**：這張表會不會被翻頁或取前 N 筆，而拿來排的那一欄分不分得出高下。答案是否定的時候，分頁的排序鍵就要在設計時寫成「那一欄加上主鍵」，而不是等症狀出現。位置式與值式兩種接續標記的取捨在 [SQL.12 分頁的排序鍵與接續標記](/backend/01-database/sql/pagination-needs-a-total-order/)。

## 表的寬度與長欄位的存放位置

**要決定的**：商品有一段很長的描述文字。它跟名稱、價格放同一張表，還是另外一張。

**兩條路**。放同一張表——它就是商品的一個屬性，拆出去要多一次連接，而且多一張表要維護。或者拆成兩張，商品表只留短欄位，描述另外一張表用同一個主鍵對上去。

設計當下放同一張表符合「一個實體一張表」的直覺，拆成兩張看起來是為了效能提前優化。

**放同一張表之後，查詢要多做什麼**。五萬列商品，描述欄各 2000 字元，兩張表其餘欄位逐列相同：

```sql
-- SQLite 3.51.0
-- 各節的表名重複，照順序跑要先清掉上一節的（SQLite 的 DROP 一次只收一張表）
DROP TABLE IF EXISTS 商品寬;
DROP TABLE IF EXISTS 商品窄;
CREATE TABLE 商品寬 (商品編號 INTEGER PRIMARY KEY, 名稱 TEXT, 價格 INT, 描述 TEXT);
CREATE TABLE 商品窄 (商品編號 INTEGER PRIMARY KEY, 名稱 TEXT, 價格 INT);

-- printf('%.2000c','x') 產生 2000 個 x 當描述；價格用 i%900+100 灑在 100 到 999 之間
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i < 50000)
INSERT INTO 商品寬 SELECT i, '商品'||i, i%900+100, printf('%.2000c','x') FROM n;

-- 窄表逐列複製寬表，除了不帶描述那一欄
INSERT INTO 商品窄 SELECT 商品編號, 名稱, 價格 FROM 商品寬;
```

跑一個**完全不碰描述欄**的查詢，兩張表都沒有索引，同一句各跑二十次取最小值（計時在行程內，不含 `sqlite3` 的啟動）：

```sql
SELECT count(*) FROM 商品寬 WHERE 價格 > 500;
SELECT count(*) FROM 商品窄 WHERE 價格 > 500;
```

| 表     | 查詢時間 | 這張表在檔案裡佔的空間 |
| ------ | -------- | ---------------------- |
| 商品寬 | 15 ms    | 98 MB                  |
| 商品窄 | 1.0 ms   | 1.1 MB                 |

**兩張表的查詢時間差十五倍，而那段查詢的文字裡沒有出現描述欄。** 差別在掃描要走過的頁數：長文字跟其餘欄位存在同一批頁面上，掃過去就得讀它們。

這也是 `SELECT *` 為什麼在寬表上特別貴（[1.13 的超量讀取段](/backend/01-database/query-anti-patterns/)），以及為什麼寬表蓋不出覆蓋索引——覆蓋索引要裝下查詢用到的每一欄，而欄位越多越難裝下。

**代價在什麼條件下浮現**。描述欄的內容長到把列撐出單一頁面、而且表大到掃描成本蓋過其他成本的時候。兩件事都隨時間發生，而且發生得很慢——**沒有任何一天它會突然變慢**，所以這一條的典型發現方式是有人去量，不是有人被擋住。

**改回來要付什麼**。把一欄搬到另一張表是一次真正的 schema 遷移：建新表、回填、改寫全部讀那一欄的查詢、再刪舊欄，中間要雙寫。完整流程在 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/)，而它的成本與那一欄被多少段程式讀成正比。

**所以設計當下要問的是**：這一欄在多少比例的查詢裡會被讀到。答案是「很少」而它又很大的時候，它跟同一張表的其他欄位的存取頻率差了一個量級，而**存取頻率差一個量級的欄位不該住在同一張表**。

## 一對多資料的切表方式

**要決定的**：一張訂單有多筆明細，也有多個標籤。要拿「這張訂單的明細總額」的時候，查詢會同時碰到幾張一對多的表。

**兩條路**。三張表各自正規化，要什麼連什麼——這是教科書的答案，而且它是對的。或者把「同時連兩個一對多」當成一個已知會出錯的形狀，在設計時就替常用的那個彙總留一條不需要連兩次的路（明細總額存在訂單表上，或者標籤不做成一對多的表）。

設計當下各自正規化明顯正確，替彙總留路看起來是反正規化，而反正規化是要有理由的。

**各自正規化之後，查詢要多做什麼**。一張訂單、兩筆明細、兩個標籤：

```sql
-- SQLite 3.51.0
-- 各節的表名重複，照順序跑要先清掉上一節的（SQLite 的 DROP 一次只收一張表）
DROP TABLE IF EXISTS 訂單;
DROP TABLE IF EXISTS 明細;
DROP TABLE IF EXISTS 標籤;
CREATE TABLE 訂單 (訂單編號 INTEGER PRIMARY KEY, 金額 INT);
CREATE TABLE 明細 (明細編號 INTEGER PRIMARY KEY, 訂單編號 INT, 小計 INT);
CREATE TABLE 標籤 (標籤編號 INTEGER PRIMARY KEY, 訂單編號 INT, 名稱 TEXT);

INSERT INTO 訂單 VALUES (101, 800);
INSERT INTO 明細 VALUES (1,101,300),(2,101,500);
INSERT INTO 標籤 VALUES (1,101,'急件'),(2,101,'禮物');

SELECT count(*) AS 連出來幾列, sum(明細.小計) AS 小計總和
FROM 訂單
JOIN 明細 ON 明細.訂單編號 = 訂單.訂單編號
JOIN 標籤 ON 標籤.訂單編號 = 訂單.訂單編號;
```

```text
連出來幾列  小計總和
4           1600
```

實際的小計總和是 800。兩筆明細各被兩個標籤複製一次，連出四列，總和翻倍（機制在 [SQL.6 連接之後的列數與空缺](/backend/01-database/sql/join-changes-rows-and-nulls/)）。同一個父列在兩張一對多的表上各有多列、而兩張表在同一段查詢裡各連一次，本篇把這個形狀叫**雙重展開**：連出來的列數是兩張表列數的乘積。

而**修法本身對不對由資料決定**。把 `sum` 改成 `sum(DISTINCT ...)`，在兩批資料上各跑一次：

```sql
SELECT sum(DISTINCT 明細.小計) FROM 訂單
JOIN 明細 ON 明細.訂單編號 = 訂單.訂單編號
JOIN 標籤 ON 標籤.訂單編號 = 訂單.訂單編號;
-- 原本的明細（300、500）：800，剛好對

UPDATE 明細 SET 小計 = 400;   -- 兩筆各 400，總和仍然是 800
-- 同一段查詢再跑一次：400，實際是 800
```

`DISTINCT` 認的是值，兩筆金額相同的明細被它當成同一筆。**這個寫法在一組資料上是對的、在另一組上少算一半，而兩次都不報錯。**

**代價在什麼條件下浮現**。同一張訂單同時有兩筆以上明細與兩個以上標籤的時候。只有一個標籤的訂單完全正常，所以這個缺陷會在資料裡潛伏很久，而且是**部分列錯**——總報表上的數字偏大，偏多少由有幾個標籤決定。

**改回來要付什麼**。不用動 schema 就能修，做法是讓每一張一對多的表在接上訂單之前先各自收成一列，或者把兩次連接拆成兩段查詢。先收成一列的寫法：

```sql
SELECT 訂單.訂單編號, 明細彙總.小計總和, 標籤彙總.標籤數
FROM 訂單
JOIN (SELECT 訂單編號, sum(小計) AS 小計總和 FROM 明細 GROUP BY 訂單編號) AS 明細彙總
  ON 明細彙總.訂單編號 = 訂單.訂單編號     -- 明細先按訂單收成一列
JOIN (SELECT 訂單編號, count(*) AS 標籤數 FROM 標籤 GROUP BY 訂單編號) AS 標籤彙總
  ON 標籤彙總.訂單編號 = 訂單.訂單編號     -- 標籤也先收成一列，連接不再複製明細
-- 101|800|2：明細是 300 與 500、或兩筆各 400，小計總和都是 800
```

成本跟分頁那一節一樣落在**找出全部中招的查詢**——而雙重展開更難找，因為症狀是一個偏大的數字，不是一個錯誤訊息。

**所以設計當下要問的是**：哪幾張表對同一個父列是一對多的，而它們會不會出現在同一段查詢裡。會的話，那個彙總在設計時就該有一條不經過雙重展開的路。

## 字串比較規則的宣告位置

**要決定的**：使用者用 email 登入，而 email 不分大小寫。這條規則寫在哪裡。

**兩條路**。寫在查詢裡——每一段比對 email 的地方都寫 `lower(email) = lower(?)`，規則看得見，而且不依賴資料庫的設定。或者寫在欄位的宣告上——替欄位宣告一套比較規則（collation），查詢直接寫等號。

設計當下寫在查詢裡看起來更明確、更可攜，因為它不依賴哪一家引擎預設怎麼比。

**寫在查詢裡之後，查詢要多做什麼**。二十萬列會員，email 欄上有索引：

```sql
-- PostgreSQL 18.6
-- 各節的表名重複，照順序跑要先清掉上一節的
DROP TABLE IF EXISTS 會員;
CREATE TABLE 會員 (會員編號 int PRIMARY KEY, email text);
INSERT INTO 會員 SELECT i, 'User'||i||'@Example.com' FROM generate_series(1,200000) i;
CREATE INDEX ix_email ON 會員(email);
ANALYZE 會員;
```

```sql
-- 規則寫在查詢裡
EXPLAIN (ANALYZE, COSTS OFF)
SELECT 會員編號 FROM 會員 WHERE lower(email) = 'user12345@example.com';
```

```text
Gather (actual time=1.809..20.367 rows=1.00 loops=1)
  Buffers: shared hit=1470
  ->  Parallel Seq Scan on "會員" (actual time=9.907..18.714 rows=0.50 loops=2)
        Filter: (lower(email) = 'user12345@example.com'::text)
        Rows Removed by Filter: 100000
```

20.4 毫秒，讀了 1470 個頁面，掃過全部二十萬列。索引在那裡而用不上——**條件把欄位包進函式裡之後，索引上存的值與條件要比的值不是同一個東西**（判斷標準與改寫方向在 [Sargable](/backend/01-database/sql/knowledge-cards/sargable/)）。

兩條修法都把它拉回索引掃描，而它們動的層不同：

```sql
-- 函式索引：規則寫進索引，查詢不動
CREATE INDEX ix_lower ON 會員(lower(email));
ANALYZE 會員;   -- 這一句不可省：上面那次 ANALYZE 跑在 ix_lower 存在之前，
                -- 沒有替這個運算式索引收統計，少了它計畫是 Bitmap Heap Scan

-- 欄位 collation：規則寫進欄位宣告，查詢連 lower() 都不必寫
-- provider=icu 指定用 ICU 這套比較規則的實作；
-- locale 的 und-u-ks-level2 是強度等級——level2 讓大小寫不算差異而重音仍算，
--   換成 level1 連重音也不算；
-- deterministic=false 不寫也建得起來，而不寫的話 ks-level2 不生效：
--   比對變回逐位元組比較，WHERE email = 'user...' 靜默回零列。
--   實測 PostgreSQL 18.6：省略它的 collation 回 0 列、寫了的回 1 列，
--   兩次 CREATE COLLATION 都成功。這一行漏掉的症狀正是本篇在講的那一種
CREATE COLLATION ci (provider = icu, locale = 'und-u-ks-level2', deterministic = false);
-- 各節的表名重複，照順序跑要先清掉上一節的
DROP TABLE IF EXISTS 會員2;
CREATE TABLE 會員2 (會員編號 int PRIMARY KEY, email text COLLATE ci);
INSERT INTO 會員2 SELECT * FROM 會員;
CREATE INDEX ix2 ON 會員2(email);
ANALYZE 會員2;
```

三段查詢並排——**函式索引那一段與原本那一段逐字相同，欄位 collation 那一段少了 `lower()`**：

```sql
-- 原本（慢）與函式索引（快）用的是同一段查詢，差別只在索引建了沒有
EXPLAIN (ANALYZE, COSTS OFF)
SELECT 會員編號 FROM 會員 WHERE lower(email) = 'user12345@example.com';

-- 欄位 collation：規則住在欄位上，查詢裡沒有任何東西在處理大小寫
EXPLAIN (ANALYZE, COSTS OFF)
SELECT 會員編號 FROM 會員2 WHERE email = 'user12345@example.com';
```

```text
原本（lower 寫在查詢裡）  Parallel Seq Scan    20.4 ms    1470 個頁面
函式索引                  Index Scan            0.027 ms      4 個頁面
欄位 collation            Index Scan            0.022 ms      4 個頁面
```

兩條修法都快，而**欄位 collation 的查詢裡沒有任何東西在處理大小寫**——規則住在欄位上，每一段查詢自動套用它。函式索引要求每一段查詢都記得寫 `lower()`，漏掉一處就是一次全表掃描加一個不分大小寫失效的比對。

**代價在什麼條件下浮現**。表長到掃描明顯變慢的時候。而這一條還有第二個代價**在單一引擎上完全量不到**：各家的預設比較規則不同，同一句 `WHERE 姓名 = 'anna'` 在 MySQL 8.4 上回四列（`Anna`、`anna`、`ANNA`、`Ánna`——它的預設 collation `utf8mb4_0900_ai_ci` 把大小寫與重音都算成同一個值），而在 SQLite 3.51 與 PostgreSQL 18 上只回逐字相同的那一列（三家的實測在 [SQL.15 字串比較與 collation](/backend/01-database/sql/string-comparison-and-collation/)）。規則沒有寫出來的時候，換一家引擎、換一個資料庫的建立參數，命中的列就變。

**改回來要付什麼**。改欄位的 collation 要重建那一欄上的全部索引，因為索引裡的排序是按舊規則建的。這件事在大表上是一次有停機風險的操作。

**所以設計當下要問的是**：這一欄的「相等」是什麼意思，而那個定義寫在哪裡。寫在每一段查詢裡的定義會被漏掉；寫在欄位上的定義由引擎替每一段查詢執行。

## 外鍵的宣告與執法

**要決定的**：訂單的顧客編號要不要宣告外鍵，以及——這是容易被略過的那一半——**那條宣告在這個環境裡會不會執法**。

**兩條路**。宣告外鍵，讓資料庫保證每一張訂單都找得到顧客。或者不宣告，由應用層自己保證，換到遷移時的彈性與少一層寫入檢查。

而這裡有第三種狀態，它是一個陷阱、不是一條可以選的路：**宣告了，而它沒有生效**。

**選了「宣告而沒有生效」之後，查詢要多做什麼**。SQLite 的外鍵執法預設是關的：

```sql
-- SQLite 3.51.0
PRAGMA foreign_keys;        -- 回 0，也就是預設不執法

-- 各節的表名重複，照順序跑要先清掉上一節的（SQLite 的 DROP 一次只收一張表）
DROP TABLE IF EXISTS 顧客;
DROP TABLE IF EXISTS 訂單;
CREATE TABLE 顧客 (顧客編號 INTEGER PRIMARY KEY, 姓名 TEXT);
CREATE TABLE 訂單 (訂單編號 INTEGER PRIMARY KEY,
                   顧客編號 INT REFERENCES 顧客(顧客編號), 金額 INT);
INSERT INTO 顧客 VALUES (1,'佳穎');
INSERT INTO 訂單 VALUES (101,1,300),(102,999,500);   -- 999 這位顧客不存在
```

兩列都寫進去了，沒有任何錯誤。同一段建表與寫入在 PostgreSQL 18.6 上，`INSERT` 被擋下來——而擋的單位是**整句 `INSERT`**，所以 101 那一列也沒有進去，訂單表跑完之後是空的：

```text
ERROR:  insert or update on table "訂單" violates foreign key constraint "訂單_顧客編號_fkey"
DETAIL:  Key (顧客編號)=(999) is not present in table "顧客".
```

孤兒列存在之後，同一份資料的兩種算法給兩個總額：

```sql
-- 直接從訂單表算
SELECT count(*), sum(金額) FROM 訂單;
-- 2|800

-- 連顧客表取姓名之後再算：102 那一列找不到顧客，被內連接濾掉
SELECT count(*), sum(訂單.金額) FROM 訂單
JOIN 顧客 ON 顧客.顧客編號 = 訂單.顧客編號;
-- 1|300
```

**兩個總額都是正確答案，而它們差 500。** 一份直接從訂單表算的報表得到 800，一份連了顧客表取姓名的報表得到 300，兩份都不報錯，而看報表的人沒有辦法從數字本身判斷哪一份對。這一節要看的是**這個差額由 schema 是否執法決定，不由那兩段查詢決定**——兩段都寫對了。

宣告與執法分家有四條路徑（連線層開關、`NOT VALID` 狀態、欄位層與表層的寫法差異、storage engine），各家引擎上的實測在 [SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)。

**代價在什麼條件下浮現**。第一筆孤兒資料寫進來的時候，而那多半是一次失敗的交易、一次部分成功的批次匯入、或一次手動修資料留下的。在那之前，有沒有執法在行為上分不出來。

**改回來要付什麼**。開啟執法之前要先清掉存量的孤兒列，而「清掉」是個業務決定——那些訂單是要補一個顧客、還是要刪掉、還是要標記。跟可空性那一節的空值一樣，這個決定當初沒有人做，所以現在要回頭做。補約束的完整順序在 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/) 的加約束段。

**所以設計當下要問的是**：這條宣告在**這個環境的這條連線上**生不生效，而答案要去系統目錄查，不是讀 `CREATE TABLE` 的文字。查法各家不同：

```sql
-- PostgreSQL 18.6
SELECT conname, convalidated, conenforced FROM pg_constraint WHERE conrelid = '訂單'::regclass;
-- convalidated = f：約束以 NOT VALID 加上，存量的列沒有檢查過
-- conenforced  = f：約束宣告成 NOT ENFORCED，新的寫入也不檢查
-- information_schema.table_constraints 的 enforced 欄只反映 conenforced，NOT VALID 的外鍵在那裡仍是 YES

-- SQLite 3.51.0
PRAGMA foreign_key_list(訂單);   -- 宣告了哪些外鍵
PRAGMA foreign_keys;             -- 這條連線有沒有開執法，0 是沒開
```

## 各項 schema 設計決定在代價浮現方式上的共同點

各節的答案並排：

| 設計時的決定             | 選了之後，查詢多付的                       | 什麼條件下才浮現                 | 改回來動的是什麼   |
| ------------------------ | ------------------------------------------ | -------------------------------- | ------------------ |
| 這一欄允不允許為空       | 否定式判斷靜默回零列、計數與排序各自分岔   | 第一個空值被寫進來               | 補值 + 加約束      |
| 這個鍵唯不唯一           | 分頁重複與遺漏、「前一列」沒有定義         | 並列 + 計畫改變 + 有人在看       | 只改查詢，難在找全 |
| 一張表裝多寬             | 不碰那一欄的查詢也慢（實測十五倍）         | 資料量長大，而且沒有哪一天會突變 | 一次欄位搬家遷移   |
| 常一起取的資料切在幾張表 | 雙重展開讓聚合算錯，而修法對不對由資料決定 | 同一父列在兩張表上都是多列       | 只改查詢，難在找全 |
| 字串的比較規則寫在哪     | 索引用不上；換引擎命中的列就變             | 表長大；或者換一家引擎           | 重建那一欄的索引   |
| 外鍵生不生效             | 同一份資料兩種算法給兩個數字               | 第一筆孤兒資料                   | 清存量 + 開執法    |

三個共同點：

**沒有一條在設計當下看得出來。** 六個決定寫進 `CREATE TABLE` 都是合法的、跑得起來的、測試會過的。它們的差別要等到資料長成某個樣子、或者查詢寫成某種形狀才出現。

**浮現的時機由資料決定，不由程式碼決定。** 所以「上線前測過了」對這六條沒有保證力——測試資料裡沒有那個空值、沒有並列、沒有孤兒列，六條就全部沉默。

**表寬與 collation 兩條的症狀含「慢」（前者十五倍、後者三個量級），其餘四條只有一個錯的數字。** 靜默回零列、分頁少一筆、聚合翻倍、報表兩種算法差 500——這四種沒有任何一個會讓程式停下來。collation 那一條兩種症狀都有：同一個引擎上是慢，換一家引擎是命中的列變了。

## 建表當下就能回答的設計問題清單

各節的最後一段各是一個問句。把它們抽出來，這幾句在寫 `CREATE TABLE` 的時候就答得出來——**每一條都不必等資料長出來**，而要看的東西不只 `CREATE TABLE` 的文字：空值代表什麼、排序的那一欄分不分得出高下、哪幾張表對同一個父列是一對多、「相等」是什麼意思，看的是領域語意；這張表會不會被翻頁或取前 N 筆、一欄在多少比例的查詢裡被讀到、那幾張一對多的表會不會出現在同一段查詢裡，看的是**預期的查詢負載**（這張表會被誰怎麼讀）；約束生不生效，看的是**這條連線上的設定**。三種輸入都在建表當下取得到，而它們不在同一個地方：

1. 這一欄的空值代表「還不知道」「不適用」還是「確定沒有」——分得開的就各自給一個值
2. 這張表會不會被翻頁或取前 N 筆，而排序的那一欄分不分得出高下
3. 這一欄在多少比例的查詢裡會被讀到，它跟同表其他欄位的存取頻率差幾個量級
4. 哪幾張表對同一個父列是一對多的，它們會不會出現在同一段查詢裡
5. 這一欄的「相等」是什麼意思，那個定義寫在欄位上還是散在每一段查詢裡
6. 這條約束在這個環境的這條連線上生不生效——去系統目錄查，不讀 `CREATE TABLE` 的文字

[1.2 schema design](/backend/01-database/schema-design/) 問的是這組表該長什麼樣（狀態責任、主鍵策略、索引、反正規化、分區、命名）；這份清單接在那些決定之後，問**長成那樣之後，往後每一次查詢要付多少**。

## 相鄰章節：schema design、查詢反模式、資料庫轉換實作與 State Ownership

- → [1.2 schema design 與資料建模](/backend/01-database/schema-design/)：這組表該長什麼樣。它的 Index 設計段已經寫著「index 設計要從查詢路徑反推」，而本篇把同一個反推套到可空性、排序鍵、表寬、一對多的切法、比較規則、外鍵這幾個決定上
- → [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)：查詢已經寫成那樣之後怎麼修。本篇的表寬與一對多兩節，是那一篇 `SELECT *` 與 N+1 兩條反模式在 schema 設計上的成因
- → [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)：各節的「改回來要付什麼」都落在它的分段流程上，可空性那一節對應它的 `Type G：加 NOT NULL constraint`，外鍵那一節對應 `Type I：加約束`
- → [1.8 State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/)：本篇問單一決定的查詢代價，那一篇問哪些資料是正式狀態、哪幾種查詢責任該分開

## 延伸閱讀：各節查詢行為的 SQL 機制篇與 PostgreSQL 查詢計畫判讀

查詢本身怎麼讀準、代價為什麼不在查詢的文字裡，在 [SQL：這個語言為什麼長這樣](/backend/01-database/sql/)。本篇六節各自指過去的那幾篇是它的機制層：[SQL.6 連接之後的列數與空缺](/backend/01-database/sql/join-changes-rows-and-nulls/) 空值與列數膨脹、[SQL.11 查詢結果的列序](/backend/01-database/sql/relations-have-no-order/) 順序、[SQL.12 分頁的排序鍵與接續標記](/backend/01-database/sql/pagination-needs-a-total-order/) 分頁、[SQL.15 字串比較與 collation](/backend/01-database/sql/string-comparison-and-collation/) collation、[SQL.18 外鍵與參照完整性](/backend/01-database/sql/foreign-key-and-referential-integrity/) 外鍵。

要在真實系統上讀計畫、而不是像本篇這樣讀三四行的輸出，走 [PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)。
