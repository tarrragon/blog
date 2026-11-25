---
title: "SQL.22 可讀性與執行代價：兩者一致與分岔的情形"
date: 2026-09-01
description: "計畫相同或語意等價時寫法差異無額外代價的原因、條件包進函式造成可讀性與效能分岔時以運算式索引解決的實測、相關子查詢拆成 CTE 同時改善可讀性與速度的量測，以及只在 schema 無法改動時才為效能改寫查詢的條件"
aliases: ["/sql/readable-and-fast-mostly-align/"]
weight: 23
tags: ["sql", "readability", "performance", "index", "cte"]
---

在 SQL 裡，好讀的寫法與執行速度快的寫法多數時候一致，只在少數特定條件下才會分岔。本篇先說明計畫相同或語意等價時寫法差異為何沒有額外代價，接著以日期函式條件實測分岔並示範透過運算式索引在 schema 層解開衝突；後半段以相關子查詢拆成 CTE 的實測說明可讀性與速度同時提升的案例，並界定唯有 schema 無法改動時才改寫查詢的條件與註記原則。

一段 SQL 同時要交給引擎執行與交給後續人員維護，這兩個目標在 SQL 中經常指向同一個寫法，因為引擎執行的是最佳化器產出的執行計畫，而非查詢文字本身（見 [SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)）。為了可讀性調整的語法結構，只要最佳化器能收斂成相同計畫，就不會增加執行成本；會改變執行次數的結構（如相關子查詢與 CTE）則是例外，本文〈相關子查詢與拆成 CTE 的實測〉將實測這類差異。

本篇討論可讀性與執行代價的取捨；關鍵字向閱讀者宣告的預期是否與實際行為一致，見 [SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)；查詢結果是否符合業務需求及查證方法，見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)。

## 計畫相同或語意相同的寫法差異

表達同一結果集的不同寫法送進 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 後，常會收斂為完全相同的執行計畫，例如 `CROSS JOIN` 加等值條件與 `JOIN ... ON` 產出的計畫逐字相同（見 [SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)）。[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/) 則示範了另一種情形：以下在 [SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/)（顧客為佳穎、宗翰、雅文，僅佳穎有兩筆訂單）上，肯定式的 `IN` 與 `EXISTS` 在 SQLite 走不同計畫，但因語意等價，在未出現效能瓶頸前同樣可優先依可讀性選用：

```sql
-- 共用資料：下過單的顧客，兩段都回 佳穎
EXPLAIN QUERY PLAN
SELECT 姓名 FROM 顧客 WHERE 顧客編號 IN (SELECT 顧客編號 FROM 訂單);
-- SCAN 顧客
-- LIST SUBQUERY 1：子查詢跑一次，把顧客編號收成一份清單

EXPLAIN QUERY PLAN
SELECT 姓名 FROM 顧客 WHERE EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
-- SCAN 顧客
-- CORRELATED SCALAR SUBQUERY 1：子查詢對顧客的每一列各跑一次
```

確認兩種寫法是否產生額外執行代價，最直接的方式是分別查詢兩者的執行計畫：若計畫相同，直接選用較易讀的寫法即可。這項方法以「能向目標引擎取得執行計畫」為前提；若當下拿不到計畫，則先以條件形狀排除明顯無法走索引的寫法（見 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)）。

## 可讀性與代價分岔的位置：條件的形狀

寫法直接影響執行代價的第一類常見位置是條件形狀：把索引欄位包進函式或運算時，引擎無法使用既有索引（見 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)），而包進函式的寫法往往比較貼近人類對業務條件的表達。

以下建立三十萬列的訂單表（一年日期均勻分布，三月約兩萬五千列），並在 `下單日` 建立索引：

```sql
CREATE TABLE 訂單 (訂單編號 INTEGER PRIMARY KEY, 顧客編號 INT, 下單日 TEXT, 金額 INT);
WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 299999)
INSERT INTO 訂單 SELECT i, i % 500, date('2021-01-01', (i % 365) || ' day'), 100 + i % 900 FROM n;
CREATE INDEX ix_日 ON 訂單(下單日);
```

統計 2021 年 3 月訂單數（SQLite 3.51，`SELECT count(*)`，各跑二十次取最小值，計時器解析度 1 毫秒）：

| 寫法                                               | 時間      |
| -------------------------------------------------- | --------- |
| `strftime('%Y-%m',下單日) = '2021-03'`             | 49 ms     |
| `下單日 >= '2021-03-01' AND 下單日 < '2021-04-01'` | 不到 1 ms |

`strftime` 寫法直接表達「所屬年月為 2021-03」，日期範圍寫法則要求閱讀者自行組合起訖邊界並確認右端為開區間；但日期範圍寫法的執行速度較快，較易讀的 `strftime` 寫法反而因無法走索引而耗時 49 毫秒。

## 好讀的寫法走不了索引時的處置：運算式索引

保留 `strftime` 寫法不改動查詢文字，改在資料庫建立對應的運算式索引：

```sql
CREATE INDEX ix_月 ON 訂單(strftime('%Y-%m',下單日));

-- 查詢與表格裡 strftime 那一行相同
EXPLAIN QUERY PLAN
SELECT count(*) FROM 訂單 WHERE strftime('%Y-%m',下單日) = '2021-03';
-- 建 ix_月 之前：SCAN 訂單 USING COVERING INDEX ix_日（整份索引掃過一遍）
-- 建 ix_月 之後：SEARCH 訂單 USING COVERING INDEX ix_月 (<expr>=?)（直接查到那個月份）
```

重跑量測後，耗時同樣降至 1 毫秒以下，且查詢文字維持原樣。

遇到可讀性與執行代價分岔時，優先評估的是能否在 schema 層以索引解決，而非急於把查詢改寫得難以閱讀。建立索引會在寫入端增加維護成本（見 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)），這項寫入代價可以量化權衡；反之，為速度犧牲可讀性雖然換來同等查詢效能，卻讓日後每次閱讀與修改都持續付出理解成本。

## 相關子查詢與拆成 CTE 的實測

在命令式程式語言中，拆分成多段常被直覺認為會增加額外開銷；在 SQL 中，當引擎未自動把相關子查詢改寫成一次計算時，拆成 CTE（Common Table Expression，`WITH` 具名子查詢）讓分組聚合只執行一次，可同時提升可讀性與速度（各引擎是否會先暫存 CTE 結果，或將外層條件推進 CTE 內部執行並不一致，實際效果仍須以執行計畫確認）。以下對照「金額高於所屬顧客平均金額的訂單張數」的一整段相關子查詢寫法與 CTE 寫法：

```sql
-- 一整段
SELECT count(*) FROM 訂單 o
WHERE o.金額 > (SELECT avg(金額) FROM 訂單 i WHERE i.顧客編號 = o.顧客編號);

-- 拆開
WITH 每人平均 AS (SELECT 顧客編號, avg(金額) AS 均 FROM 訂單 GROUP BY 顧客編號)
SELECT count(*) FROM 訂單 o JOIN 每人平均 p ON p.顧客編號 = o.顧客編號
WHERE o.金額 > p.均;
```

另建測試資料表，固定顧客數為 500 位，並將總列數 `N` 依序翻倍為 5000、10000、20000、40000：

```sql
CREATE TABLE 訂單 (訂單編號 INTEGER PRIMARY KEY, 顧客編號 INT, 金額 INT);
WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < N-1)
INSERT INTO 訂單 SELECT i, i % 500, 100 + (i * 37) % 900 FROM n;
CREATE INDEX ix_顧 ON 訂單(顧客編號);
```

在 SQLite 3.51 上各資料量執行二十次取最小值：

| 列數  | 一整段 | 拆成 CTE |
| ----- | ------ | -------- |
| 5000  | 9 ms   | 1 ms     |
| 10000 | 33 ms  | 3 ms     |
| 20000 | 126 ms | 7 ms     |
| 40000 | 551 ms | 15 ms    |

總列數每次翻倍時，一整段相關子查詢的耗時分別成長為 3.7、3.8 與 4.4 倍（近似平方成長）；CTE 版本最後一段的比值為 2.1（線性成長；5,000 列與 10,000 列兩組因接近 1 毫秒計時解析度故不計比值）。這項倍數關係成立的前提是顧客數固定：總列數翻倍代表每位顧客的平均訂單數同步翻倍，使相關子查詢對每一列掃描的筆數成倍放大；若顧客數與列數等比例成長，差距會較緩和。執行計畫清楚揭示了原因：相關子查詢對外層每一列重複計算一次該顧客平均（見 [Subquery（子查詢）](/backend/01-database/sql/knowledge-cards/subquery/)），而 CTE 先將每位顧客的平均統一算完一次，再與訂單表連接：

```text
一整段
SCAN o
CORRELATED SCALAR SUBQUERY 1                   對外層 o 的每一列各執行一次
   SEARCH i USING INDEX ix_顧 (顧客編號=?)

拆成 CTE
CO-ROUTINE 每人平均                             每位顧客的平均算一次
   SCAN 訂單 USING INDEX ix_顧
SCAN p
SEARCH o USING INDEX ix_顧 (顧客編號=?)         拿每人平均去連接訂單
```

拆成 CTE 明確表達「每位顧客只有一個平均值」，既讓閱讀者看清計算層次，也讓引擎避免對同組資料重複掃描。不過若外層另有高選擇率過濾條件（例如只查單一顧客）而引擎選擇將 CTE 預先物化、阻擋條件下推，CTE 反而會先彙總整張表而變慢，因此拆改後仍須對照執行計畫。

## 為速度扭曲寫法所依賴的資料庫狀態

[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/) 已實測同一組查詢的耗時排名會隨索引增減而反轉：在查詢文字未動的前提下，建立索引就能讓最慢的寫法躍升至與最快寫法同一量級。為了遷就當下資料庫狀態而扭曲寫出的難讀查詢，在日後補上索引或資料分布改變後便失去原本的效能理由，難讀的程式碼卻會長期留在程式庫裡；反之，清晰表達意圖的可讀寫法不隨資料庫狀態失效。

[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/) 列出的四項代價決定因子（資料量、分布、索引、統計資訊）全屬於資料庫狀態，不在查詢文字之中，因此效能調校的預設位置是 schema 與執行計畫，查詢文字則專注於準確傳達意圖。

## 無法調整 schema 或加索引寫入代價過高時改寫查詢：成立條件與註記原則

唯有在 schema 層無法調整時——例如連線目標為唯讀複本、使用不可修改結構的外部廠商資料庫，或新增索引的寫入放大成本超出系統容許上限——才適合在查詢文字層為效能妥協可讀性。

僅讀難讀的查詢文字，後續維護者無法得知當初因結構無法變動而改寫的限制，極可能以為它只是寫得繁瑣而「順手改寫回較簡潔的版本」，導致線上效能突然退化。緊鄰查詢附上註解——記明哪一層結構無法變動以及改寫前後的執行計畫與量測差異——能保留這項歷史限制供後續維護者查核。

在真實查詢設計中，可讀性與執行代價的取捨會與需求釐清、資料前提驗證及邊界盤點同時發生；[SQL.23 查詢設計的完整示範：把「哪幾天氣溫比前一天高」從需求做到上線](/backend/01-database/sql/requirement-to-shipped-query/) 以「哪幾天氣溫比前一天高」示範如何把這套判斷從規格追問一路做到索引量測與上線前檢查。
