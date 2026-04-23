---
title: "Database"
date: 2026-04-23
description: "說明 database 在後端系統中如何承擔正式狀態、查詢與一致性責任"
weight: 136
---

Database 的核心概念是「保存服務正式狀態並提供可查詢資料邊界」。它通常承擔 [source of truth](../source-of-truth/)、[transaction](../transaction/)、索引、約束、備份、權限與 [data lifecycle](../data-lifecycle/) 責任。

## 概念位置

Database 是產品狀態與操作證據的核心依賴。Cache、search index、read replica、event stream 與報表通常都是衍生資料；資料衝突時，團隊需要知道哪個 database 或資料表承擔正式判斷。

## 可觀察訊號與例子

系統需要 database 設計的訊號是資料要被長期保存、查詢、修改與稽核。訂單服務需要保存訂單狀態、付款紀錄、出貨狀態與取消原因；這些資料會影響客服、帳務、出貨與報表。

## 設計責任

Database 設計要包含 [schema migration](../schema-migration/)、[transaction boundary](../transaction-boundary/)、[isolation level](../isolation-level/)、[connection pool](../connection-pool/)、備份回復、權限、資料保留與觀測指標。操作上要能看 query latency、lock、[replication lag](../replication-lag/)、connection pool 使用量與錯誤分類。
