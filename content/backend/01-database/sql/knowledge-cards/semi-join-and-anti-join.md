---
title: "Semi-join 與 Anti-join（半連接與反連接）"
date: 2026-09-02
description: "看到 EXISTS 或 NOT EXISTS 時，對照它在關聯代數中的運算定義與列數上限"
aliases: ["/sql/knowledge-cards/semi-join-and-anti-join/"]
weight: 20
tags: ["sql", "join", "exists", "relational-algebra", "semi-join", "anti-join", "knowledge-card"]
---

Semi-join（半連接）把兩個 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 依條件配對後，僅輸出左側集合中在右側找得到配對對象的列；結果只包含左側欄位，且左側每一列至多出現一次。Anti-join（反連接）則輸出互補的子集：左側集合中在右側配對不到任何對象的列，結果欄位同樣只來自左側。

SQL 沒有為半連接與反連接保留獨立的連接關鍵字，通常改用 `EXISTS` 與 `NOT EXISTS` 表達（子查詢慣例寫成 `SELECT 1`，因為 `EXISTS` 只檢驗子查詢是否產出至少一列、不讀取投影值）：

```sql
-- 半連接：下過單的顧客
SELECT 姓名 FROM 顧客
WHERE EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);

-- 反連接：從未下單的顧客
SELECT 姓名 FROM 顧客
WHERE NOT EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
```

## 「半」指輸出僅帶出單側欄位

以下比較三種運算作用在同一對關係上的輸出欄位與列數上限：

| 運算   | 輸出欄位     | 結果列數         | 常見 SQL 寫法  |
| ------ | ------------ | ---------------- | -------------- |
| 連接   | 左右兩側皆有 | 可能超過左側列數 | `JOIN ... ON`  |
| 半連接 | 僅左側欄位   | 至多等於左側列數 | `EXISTS`、`IN` |
| 反連接 | 僅左側欄位   | 至多等於左側列數 | `NOT EXISTS`   |

在半連接與反連接中，右側資料表僅作為存在性檢查條件，其欄位無法出現在輸出內。只要查詢需要輸出右側欄位，就必須改用完整連接，選用依據見 [SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)。

## 列數上限免除事後去重

半連接只檢查右側是否存在至少一筆配對，配對筆數不影響結果——不論一位顧客有 2 筆或 20 筆訂單，`EXISTS` 都只讓她出現一次。相同需求若改寫成 `JOIN`，該顧客會依訂單筆數重複出現，必須補上 `DISTINCT` 才能消除膨脹出來的列（見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。

因此，查詢必須靠 `DISTINCT` 壓回筆數時往往是一項警訊：需求本身屬於存在性檢查，卻使用了會展開配對的連接運算。

## 反連接的 SQL 寫法：NOT EXISTS 與外連接加 IS NULL

除了 `NOT EXISTS` 直接表達「找不到配對」之外，也能利用 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 先保留左側全部列，再挑出右側補上 `NULL` 的列：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.訂單編號 IS NULL;
```

兩種寫法回傳同一批列，但機制不同：`NOT EXISTS` 由條件直接判定存在性，`LEFT JOIN ... IS NULL` 則依賴外連接補入的 `NULL` 作為未配對標記（前提是 `WHERE` 檢查的右表欄位在配對成功時必定非空，通常是右表主鍵或非空連接鍵，否則會混入原本該欄即為 `NULL` 的配對列）。

`NOT IN` 的行為與上述兩種寫法不同：一旦子查詢回傳的清單內含任何一個 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)，整段查詢就會靜默回傳零列且不報錯；外層比對欄位為 `NULL` 時也會被濾除。因此撰寫反連接查詢時，安全寫法為 `NOT EXISTS` 或外連接加 `IS NULL`（推導見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。

## 跟其他概念的關係

半連接與反連接和連接一樣屬於導出運算：半連接等價於連接後僅投影左側欄位再去重，反連接等價於左側關係減去半連接結果。[Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/) 的基本運算清單常只列到連接，但在實務查詢裡，所有檢查存在與不存在的需求——例如找出下過單的顧客、找出未下單的顧客、找出沒有五星評價的訂單——底層都歸結到這兩個運算。

這兩個運算是否以專屬名稱出現在 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 內，隨引擎實作而異。DuckDB 1.5.5 會在計畫中標示 `Join Type: SEMI`；SQLite 3.51.0 沒有對應的獨立運算子，會把 `EXISTS` 子查詢編譯為帶有 `LIMIT 1` 計數器的迴圈，找到第一筆配對即提前跳出——兩者語意等價，但 SQLite 的計畫上只會顯示子查詢節點。

半連接與 [Cartesian Product（笛卡兒積）](/backend/01-database/sql/knowledge-cards/cartesian-product/) 分別構成連接結果列數的兩個端點。笛卡兒積是缺少條件時的列數上限，等於兩側列數相乘；半連接將結果上限壓低至左側列數，不受右側重複配對影響；一般連接的結果列數則落在兩者之間，取決於配對鍵的重複程度。

## 延伸閱讀：存在性選型、自連接與代價實測

- `IN`、`EXISTS` 與 `JOIN` 在列數與可取用欄位上的選用依據：[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)
- 從業務敘述推導至反連接與分組計數的差別：[SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)
- 同一張表的兩列互相比對時的存在性寫法：[SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)
- 不同寫法在索引與資料分布變化下的耗時實測：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)
