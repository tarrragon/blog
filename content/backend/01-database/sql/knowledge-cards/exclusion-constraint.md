---
title: "Exclusion Constraint（排除約束）"
date: 2026-11-12
description: "要讓資料庫保證「同一個資源的兩段時間不重疊」這類唯一鍵寫不出來的規則，或讀到 EXCLUDE USING gist 時"
weight: 21
tags: ["sql", "constraint", "postgresql", "concurrency", "knowledge-card"]
---

排除約束是 PostgreSQL 的一種[約束](/backend/01-database/sql/knowledge-cards/constraint/)：由幾組「欄位與比較運算子」組成，新的一列跟既有的某一列在每一組上的比較都成立時，拒絕新的那一列。唯一鍵是它的特例——每一組的運算子都是 `=`。把運算子換成區間的重疊比較 `&&`，就能表達唯一鍵寫不出來的規則：同一間會議室的兩段預約不能重疊、同一位員工的兩段班不能重疊。

```sql
CREATE EXTENSION btree_gist;  -- 讓整數這類一般欄位也能放進 GiST 索引
CREATE TABLE shift (
  emp_id int NOT NULL,
  during tstzrange NOT NULL,  -- [起, 訖) 的時間區間
  EXCLUDE USING gist (emp_id WITH =, during WITH &&)
);
```

## 由索引在寫入時檢查的規則

約束靠一個支援那些運算子的[索引](/backend/01-database/sql/knowledge-cards/indexing/)執行，重疊比較要用 GiST 索引。新的一列寫入時要在索引裡登記自己，登記前先找有沒有衝突的列；找到另一個交易還沒提交的衝突列時，等那個交易結束，對方提交就拒絕這一列、對方回滾就放行。這個「等待再判定」讓規則在並行寫入下也成立。用觸發器或應用程式先查再插入的寫法，在 PostgreSQL 預設的 `READ COMMITTED` 下查不到對方還沒提交的列，兩段重疊的班都會寫進去；SQL.20 實測了兩種寫法的差別。排除約束對新增與修改都生效，改時段的 `UPDATE` 也會被檢查。

## 跟其他概念的關係

`UNIQUE` 指「某幾欄的值不能相等」；排除約束指「某幾欄在指定的比較下不能同時成立」，相等只是其中一種比較。它擋的是寫入偏斜（write skew）這一類異常裡能寫成「兩列不能共存」的那一部分；條件是幾列的合計（請假合計不超過上限）時寫不成排除約束，要靠 `SERIALIZABLE`。SQLite 與 MySQL 都沒有排除約束，同樣的規則在 SQLite 上要靠觸發器加上寫入鎖的排隊，換引擎時這是[資料庫引擎](/backend/01-database/sql/knowledge-cards/database-engine/)之間要動到設計的差異。

## 往下走

- 並行寫入下排除約束與觸發器、`SERIALIZABLE` 的實測對照：[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)
- 區間型別與排除約束的其他用法：[PostgreSQL SQL Features：PG 早就有的、MySQL 8.0 才補的、PG 仍領先的](/backend/01-database/vendors/postgresql/sql-features-baseline/) 的〈Range Types + Exclusion Constraints〉
- 兩筆各自合法、合起來違反條件的異常：[Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)
