---
title: "Exclusion Constraint（排除約束）"
date: 2026-11-12
description: "需要由資料庫保證同一資源兩段時間不可重疊，或讀到 PostgreSQL 的 EXCLUDE USING gist 語法時"
weight: 21
tags: ["sql", "constraint", "postgresql", "concurrency", "knowledge-card"]
---

Exclusion constraint（排除約束）是 PostgreSQL 提供的 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 類型，由多組「欄位與比較運算子」構成：當新寫入的列與表中既有列在所有組別的比較條件同時成立時，資料庫拒絕寫入。`UNIQUE` 是所有組別皆使用 `=` 運算子的特例；把運算子換成區間重疊比較 `&&`，即可強制唯一鍵無法表達的「同一會議室預約不重疊」或「同一員工班表不重疊」規則：

```sql
CREATE EXTENSION btree_gist;  -- 讓整數這類一般欄位也能放進 GiST 索引
CREATE TABLE shift (
  emp_id int NOT NULL,
  during tstzrange NOT NULL,  -- [起, 訖) 的時間區間
  EXCLUDE USING gist (emp_id WITH =, during WITH &&)
);
```

## 透過索引在寫入時攔截並行衝突

排除約束仰賴支援對應運算子的 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 執行（區間重疊須使用 GiST 索引）。新列寫入時會先在索引中檢查衝突列；若發現另一 [Transaction（交易）](/backend/knowledge-cards/transaction/) 尚未提交的衝突列，資料庫會等待對方結束——對方提交則拒絕新列，對方回滾則放行。這項等待機制使排除約束在並行寫入下仍能維持正確性，相較之下，以觸發器或應用程式先查再寫在 PostgreSQL 預設的 `READ COMMITTED` 下看不到未提交列而會寫入重疊班表（實測見 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)）。排除約束同時作用於 `INSERT` 與 `UPDATE`。

## 跟其他概念的關係

`UNIQUE` 禁止指定欄位組出現相等的值；排除約束禁止任兩列在指定比較運算下同時成立，涵蓋相等以外的區間交集等關係。排除約束能擋下可表達為「任兩列不可共存」的寫入偏斜（[Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)），且在表層強制執法、不受連線隔離等級影響；若規則涉及多列總和（例如單人每月請假總時數上限），則無法寫成排除約束，須改為鎖定父資源列（`SELECT ... FOR UPDATE`），或由所有寫入路徑一致採用 `SERIALIZABLE` 隔離等級並搭配重試。SQLite 與 MySQL 不支援排除約束，在 SQLite 上須改以觸發器搭配寫入鎖排隊實作，跨 [Database Engine（資料庫引擎）](/backend/01-database/sql/knowledge-cards/database-engine/) 遷移時須同步調整並行設計。

## 延伸閱讀：並行實測與區間型別

- 並行寫入下排除約束、觸發器與 `SERIALIZABLE` 的實測對照：[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)
- 區間型別與排除約束的進階用法：[PostgreSQL SQL Features：PG 早就有的、MySQL 8.0 才補的、PG 仍領先的](/backend/01-database/vendors/postgresql/sql-features-baseline/) 的〈Range Types + Exclusion Constraints〉一節
- 兩筆各自合法但合併違法之並行異常：[Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)
