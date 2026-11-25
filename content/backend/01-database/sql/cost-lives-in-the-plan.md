---
title: "SQL.17 查詢的代價：資料分布、索引與寫法各自的影響"
date: 2026-08-31
description: "尋找重複值的分組、自連接與 EXISTS 在有無索引與不同重複次數下的實測耗時與執行計畫、函式包住索引欄的邊界，以及比較查詢快慢前須補齊的條件與計畫查詢方式"
aliases: ["/sql/cost-lives-in-the-plan/"]
weight: 18
tags: ["sql", "cost", "query-plan", "index", "performance"]
---

這篇說明決定 SQL 查詢執行代價的因素與驗證方法：先以尋找重複 email 的分組、自連接與 `EXISTS` 寫法在有無索引下實測耗時與執行計畫；再透過提高重複次數實測分組與自連接在演算法結構上的差異；接著界定寫法本身影響代價的邊界（條件把索引欄包進函式導致無法走索引）；最後整理比較查詢快慢時必須補齊的資料庫狀態條件與查閱執行計畫的做法。

同一段 SQL 的執行代價由資料分布與可用索引決定，而不單由查詢寫法決定。建立索引後，分組、自連接與 `EXISTS` 的執行耗時排名會直接重排，即使這三段查詢文字未改動任何一字。

## 找重複 email 的分組、自連接與 EXISTS 寫法

給定一張包含 `id` 與 `email` 欄位的 `Person` 資料表，查詢目標是找出出現超過一次的 email，常見寫法如下。

**分組**：依 `email` 分組後篩選列數大於一的組：

```sql
SELECT email FROM Person GROUP BY email HAVING count(*) > 1;
```

**自連接**：讓資料表出現兩次並配對 `email` 相同但 `id` 不同的列（[SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/) 說明同表出現兩次與別名規則）：

```sql
SELECT DISTINCT p1.email FROM Person p1
JOIN Person p2 ON p1.email = p2.email AND p1.id <> p2.id;
```

**`EXISTS`**：對每一列檢查是否存在另一列具有相同 `email` 且不同 `id`（[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/) 對照存在性查詢的寫法選擇）：

```sql
SELECT DISTINCT email FROM Person p
WHERE EXISTS (SELECT 1 FROM Person q WHERE q.email = p.email AND q.id <> p.id);
```

## 有無索引時分組、自連接與 EXISTS 的實測時間與計畫

這三種寫法回傳相同的結果。以下量測在 SQLite 3.51 上執行，未執行 `ANALYZE`（收集統計資訊的指令），每段查詢各跑二十次取最小值；計時器解析度為 1 毫秒，低於解析度時表格記為「不到 1」。

這組量測結果的變化形狀取決於引擎的執行模型：SQLite 採逐列處理並將相關子查詢編譯成逐列巢狀執行，因此加上索引能直接降低 `EXISTS` 每次查找的單價。向量化引擎（例如 DuckDB，一次批次處理多列）採用不同的執行路徑，三種寫法的耗時比例也不同。此外，本篇實測資料量皆可完整常駐記憶體；當工作集超出記憶體容量時，索引隨機回表（random I/O）與全表順序掃描（sequential I/O）的成本切換點會隨之移動。這組量測結果說明的是「執行代價由資料分布與可用存取路徑決定」的機制，在不同硬體或引擎版本上絕對毫秒數會改變，應對照同一欄內的相對倍數。

實測資料表共有七千列，其中單一 email（`hot@x.com`）重複兩千次：

```sql
CREATE TABLE Person (id INTEGER PRIMARY KEY, email TEXT);

-- 以遞迴 CTE 產生 5,000 列測試資料（加上重複列共 7,000 列）
WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 4999)
INSERT INTO Person SELECT i, 'u' || i || '@x.com' FROM n;

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 1999)
INSERT INTO Person SELECT 100000 + i, 'hot@x.com' FROM n;

-- 有索引的那一欄另外跑：CREATE INDEX ix ON Person(email);
```

| 寫法     | `email` 沒有索引 | `email` 有索引 |
| -------- | ---------------- | -------------- |
| 分組     | 1 ms             | 不到 1 ms      |
| 自連接   | 217 ms           | 186 ms         |
| `EXISTS` | 1378 ms          | 1 ms           |

未建索引時 `EXISTS` 最慢（1378 毫秒），建立索引後耗時降至 1 毫秒，與分組落入同一量級——在查詢文字未動的前提下相差三個量級。分組原本就接近計時器下限；自連接從 217 毫秒降至 186 毫秒（為排除量測雜訊，另行重建資料重測五輪、每輪二十次取最小值，五輪皆是有索引較快，但降幅遠不到一個量級）。

對照 `EXISTS` 建索引前後的執行計畫即可看清耗時巨變的原因。未建索引時：

```text
|--SCAN p
|--CORRELATED SCALAR SUBQUERY 1
|  `--SCAN q
`--USE TEMP B-TREE FOR DISTINCT
```

`CORRELATED` 表示相關子查詢引用了外層欄位，必須針對外層七千列逐一執行，且每次執行都是全表掃描（`SCAN q`）。

建索引之後同一段查詢的計畫變為：

```text
|--SCAN p USING COVERING INDEX ix
`--CORRELATED SCALAR SUBQUERY 1
   `--SEARCH q USING COVERING INDEX ix (email=?)
```

子查詢仍逐列執行，但每次操作從全表掃描（`SCAN`）變成透過 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 定位（`SEARCH`），逐列結構未變，每次查找的單價則大幅下降。`COVERING` 覆蓋索引表示索引本身已涵蓋查詢所需欄位、無須回主表讀取（計畫術語見 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)，寫入端維護代價見 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)）。

## 重複次數改變時分組與自連接的實測

除索引配置外，鍵值的重複度也會使不同演算法結構的耗時分岔。以下重複度實測固定表大小為五萬列且不建索引，只調整單一重複 email 的重複次數 `k`（依序為 10、200、2000）：

```sql
CREATE TABLE Person (id INTEGER PRIMARY KEY, email TEXT);

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 50000-k-1)
INSERT INTO Person SELECT i, 'u' || i || '@x.com' FROM n;

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < k-1)
INSERT INTO Person SELECT 1000000 + i, 'hot@x.com' FROM n;
```

| 重複次數 | 配對數    | 分組 | 自連接 |
| -------- | --------- | ---- | ------ |
| 10       | 90        | 8 ms | 30 ms  |
| 200      | 39,800    | 8 ms | 32 ms  |
| 2000     | 3,998,000 | 8 ms | 232 ms |

分組的耗時維持在 8 毫秒不變；自連接在重複次數達到 2000 時耗時暴增超過七倍。

這組量測結果的關鍵在「配對數」欄位。自連接必須把每一對相同 email 的不同列實際配出來再交由 `DISTINCT` 去重，配對數為 n(n−1)，隨重複次數呈平方成長（重複次數放大十倍，配對數放大百倍）。當重複次數較小時，五萬列掃描的固定成本佔主導；當配對數增至近四百萬時，配對展開成本大幅拉高總耗時。分組完全不展開兩兩配對，因此不受重複次數影響。兩者在此的差距源自演算法結構，而非參數調校。

## 寫法阻擋索引的邊界：條件把索引欄包進函式

除了展開配對的運算結構差異外，「代價由資料與索引決定」還有另一項前提：查詢條件的形狀必須允許引擎使用索引。沿用含索引 `ix` 的七千列 `Person` 表，比較兩種等值條件：

```sql
EXPLAIN QUERY PLAN SELECT * FROM Person WHERE lower(email) = 'hot@x.com';
-- `--SCAN Person
-- 索引 ix 存的是 email 本身，條件比對的是 lower() 算完的結果，
-- 引擎在索引上找不到那個值，只能掃全表、逐列算完再比

EXPLAIN QUERY PLAN SELECT * FROM Person WHERE email = 'hot@x.com';
-- `--SEARCH Person USING COVERING INDEX ix (email=?)
-- 條件直接比 email，引擎在索引上查找
```

當資料表的 `email` 皆為小寫時，兩段查詢回傳同一批兩千列（`lower()` 版本另外會命中大小寫混寫的資料）。在此情境下，查詢寫法直接決定索引能否被納入可行路徑——條件形狀先決定哪些存取路徑可行，資料分布與索引再決定最佳化器挑哪一條路徑。判斷條件是否適用索引的標準與改寫方向（把函式條件改寫成範圍比較、將運算移至常數側，或建立運算式索引），見 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)。

## 比較兩段查詢的快慢：要補上的條件與向引擎要計畫的做法

離開資料表列數、欄位值分布形態、已建立索引與 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)（是否執行過 `ANALYZE`）等資料庫狀態，單獨比較兩段 SQL 的快慢並無固定答案（[SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/) 示範統計資訊如何改變計畫）。

這四項狀態各自影響不同環節：資料量決定全表掃描等固定成本是否被放大；資料分布決定寫法是否落入最壞複雜度（如同高重複度實測中自連接耗時激增）；索引決定單次查找的成本（如同有無索引實測中加建索引使 `EXISTS` 加速三個量級）；統計資訊決定最佳化器能否正確估算各路徑代價。

由於這些狀態皆存在於資料庫而非查詢文字裡，單一狀態下量得的執行計畫只反映當下的排名；當索引調整或資料量放大後，最佳化器可能切換演算法，因此需要再次取得計畫對照前後變化。各引擎查閱計畫的語法不同（SQLite 使用 `EXPLAIN QUERY PLAN`，PostgreSQL 使用 `EXPLAIN`）。真實系統的執行計畫包含巢狀節點與估計列數，[PostgreSQL Query Optimization：EXPLAIN、auto_explain、pg_hint_plan 與 planner 選錯 plan 的 production case](/backend/01-database/vendors/postgresql/query-optimization/) 說明了 `EXPLAIN`、`EXPLAIN ANALYZE` 與 `auto_explain` 工具的分工，以及誤選全表掃描、誤選 nested loop、缺少多欄位統計與未啟用平行執行的實務案例。

因為代價主要由資料與索引決定，撰寫 SQL 時可優先考量可讀性。[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/) 比較免費的寫法差異、條件形狀造成可讀性與效能分岔，以及將相關子查詢拆成 CTE（`WITH` 具名子查詢）後在四萬列上快逾三十倍的實測，並整理分岔時調整 schema 或調整查詢的判斷標準。
