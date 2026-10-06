---
title: "Partial Index（部分索引）"
date: 2026-10-06
description: "列表或查詢只看表裡的一小類列、而其餘大宗資料讓索引又大又讀得慢時，查部分索引的寫法、查詢要帶什麼條件規劃器才會用它，以及排除條件要放在哪張表"
weight: 465
tags: ["backend", "database", "postgresql", "index", "knowledge-card"]
---

Partial index 是只收表裡符合某個條件的列的索引，寫法是在建索引時加 `WHERE`，例如 `CREATE INDEX ... ON links (created_by, id DESC) WHERE send_id IS NULL` 只收一般連結。查詢的條件能推出索引的條件時（查詢也帶著 `send_id IS NULL`），規劃器才會用它。它讓「只看一小類列」的查詢跳過其餘的大宗資料，索引本身也只有那一小類的大小。它和 [Table Partitioning](/backend/knowledge-cards/table-partitioning/) 都在單一資料庫內把表裡的某一類資料分開處理，差別在 partial index 只分開索引、資料仍在同一張表；查詢讀的量要不要跟著表一起成長，見 [1.19 資料表長期成長的成本](/backend/01-database/table-growth-query-cost/)。其他中文資料常寫作部分索引或條件索引；MySQL（InnoDB）沒有這個功能。

## 概念位置

| 做法                         | 讀的量由什麼決定                    | 前提                     |
| ---------------------------- | ----------------------------------- | ------------------------ |
| 一般索引，條件當篩選         | 每頁筆數 × 大宗資料與目標資料的比例 | 無                       |
| 一般索引，排除條件在另一張表 | 同上，而且每一列多查一次另一張表    | 無                       |
| Partial index                | 每頁筆數                            | 分類用的欄位在同一張表上 |

索引只能包含同一張表的欄位，所以「這一列屬於哪一類」要拿來篩選時，那一欄要放在被查的表上。唯一約束也可以寫成 partial index（`CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL`），讓已經軟刪除的列不佔用唯一值，見 [Soft Delete](/backend/knowledge-cards/soft-delete/)。

## 可觀察訊號與例子

- **列表的第一頁讀了很多頁**：`EXPLAIN (ANALYZE, BUFFERS)` 的 `Rows Removed by Filter` 是回傳筆數的好幾十倍，被丟掉的都是同一類大宗資料。
- **建了 partial index 卻沒被用**：查詢的條件推不出索引的條件，例如索引寫 `WHERE send_id IS NULL`，查詢寫的是 `WHERE NOT EXISTS (...)`；或條件用了參數，規劃器在通用計畫裡無法確定參數值會符合索引的條件。
- **實例**：短網址服務的連結表九成九是發送建立的收件人連結。在 200 萬列的測試資料上，連結列表只列一般連結時，用一般索引加篩選第一頁讀 158 頁，用 partial index 讀 3 頁；這個索引只有 624 kB，同一份資料的完整索引是 60 MB。

## 設計責任

先確認目標那一類的列在查詢裡是固定的條件，而不是使用者每次選的值：固定的條件才寫得進索引。決定時寫下兩件事：分類用的欄位放在哪一張表、查詢的程式要帶著能推出索引條件的條件：規劃器的要求是推得出來，最保險的寫法是和索引逐字相同；條件用了參數時，要確認在通用計畫下也推得出來。ORM 產生的查詢要確認它把條件寫成規劃器推得出來的形式。
