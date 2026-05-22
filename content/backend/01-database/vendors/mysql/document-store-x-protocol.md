---
title: "MySQL Document Store / X Protocol"
date: 2026-05-22
description: "MySQL Document Store、X Protocol、JSON collection、SQL interoperability、MongoDB-like API 與使用邊界"
tags: ["backend", "database", "mysql", "document-store", "json"]
---

MySQL Document Store / X Protocol 的核心責任是說明 MySQL 如何在 relational engine 內提供 JSON document workflow。Document Store 讓 application 透過 X Protocol 與 CRUD API 操作 collection，但資料仍落在 MySQL 的 storage、transaction、backup 與 permission 模型裡。

本文的判讀錨點是：Document Store 是 MySQL 內的 document access pattern，而非 MongoDB 等專用 document database 的完整替代。它適合 relational schema 旁邊的 flexible JSON，但不適合把主要資料模型都藏進無治理 JSON。

官方文件路由的核心責任是固定 X Protocol claim。實作前先查 [MySQL 8.4 Document Store](https://dev.mysql.com/doc/refman/en/document-store.html)；本文最後檢查日是 2026-05-22。

## Responsibility Boundary

Responsibility boundary 的核心責任是把 Document Store 和 SQL table 關係說清楚。

| 面向        | Document Store                      | SQL table / JSON column    |
| ----------- | ----------------------------------- | -------------------------- |
| Access API  | X Protocol、CRUD-style API          | SQL、JSON function         |
| Storage     | MySQL InnoDB                        | MySQL InnoDB               |
| Transaction | MySQL transaction                   | MySQL transaction          |
| Governance  | 仍需 backup、role、audit、migration | 仍需 schema / index review |
| Query power | document-friendly access            | SQL join、index、optimizer |

Document Store 的價值是降低 flexible object 的開發摩擦。它不免除資料合約、index、migration、backup 與 audit 的責任。

## Suitable Use Cases

Suitable use cases 的核心責任是找出 document pattern 的合理位置。

| 情境                     | 適合原因                         |
| ------------------------ | -------------------------------- |
| Profile / preference     | 欄位變動快、查詢條件少           |
| Integration payload      | 需要保存外部 JSON 原文           |
| Feature flag / config    | 讀多寫少、schema 變化頻繁        |
| Hybrid relational + JSON | 主體 relational，局部 flexible   |
| Prototype                | 先探索欄位，再逐步 relationalize |

Document Store 最適合局部 flexible data。若核心 query 需要大量 join、aggregation、transaction invariant，應把穩定欄位拉回 relational schema。

## Query and Index

Query and index 的核心責任是避免 JSON 查詢變成不可觀測黑箱。

| 問題              | 審查方向                                     |
| ----------------- | -------------------------------------------- |
| 常用 filter       | 是否需要 generated column / functional index |
| Sort / pagination | 是否能走 index                               |
| Schema drift      | document version / validation                |
| Large document    | update amplification、network payload        |
| Analytics         | 是否應 ETL 到 OLAP / warehouse               |

MySQL JSON 查詢可以從 generated column 建 index。正式服務要把常用 JSON path 寫進 query contract，避免每次都掃完整 document。

## Migration Boundary

Migration boundary 的核心責任是讓 document data 可演進。Document 欄位雖然 flexible，但 application 仍會依賴某些 key；這些 key 一旦進入 workflow，就要有版本與 validation。

最小治理：

1. Document version field。
2. Required key validation at application boundary。
3. Backfill script for new required key。
4. Index review for promoted key。
5. Export / backup restore validation。

當 JSON key 變成 join key、permission key 或 reporting key，應評估搬到 relational column。

## No-Go Conditions

No-go conditions 的核心責任是指出 Document Store 的邊界。

| 訊號                         | 建議路由                                 |
| ---------------------------- | ---------------------------------------- |
| 主要資料都是 nested document | MongoDB / document database evaluation   |
| 大量 document aggregation    | OLAP / search / document-oriented engine |
| JSON path 已成核心 index     | relationalize key 或 generated column    |
| 需要跨 document complex join | relational schema                        |
| 需要 schema governance       | migration + validation                   |

Document Store 要服務於 flexible edge，而非取代資料建模。當 flexible area 穩定下來，就把它納入 schema governance。

## 下一步路由

Document Store / X Protocol 完成後，JSON 與 SQL 能力讀 [Modern SQL Features](../modern-sql-features/)；若主要資料模型是 document，讀 [MongoDB](/backend/01-database/vendors/mongodb/)；migration 到 PostgreSQL JSONB 可讀 [MySQL to PostgreSQL](../migrate-to-postgresql/)。
