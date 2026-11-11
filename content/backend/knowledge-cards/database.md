---
title: "Database"
date: 2026-04-23
description: "說明 database 在後端系統中如何承擔正式狀態、查詢與一致性責任"
weight: 137
---

Database 的核心概念是「保存服務正式狀態並提供可查詢資料邊界」。它通常承擔 [source of truth](/backend/knowledge-cards/source-of-truth/)、[transaction](/backend/knowledge-cards/transaction/)、索引、約束、備份、權限與 [data lifecycle](/backend/knowledge-cards/data-lifecycle/) 責任。

## 跟其他概念的關係

Database 是產品狀態與操作證據的核心依賴。Cache、search index、read replica、event stream 與報表通常都是衍生資料；資料衝突時，團隊需要知道哪個 database 或資料表承擔正式判斷。 可先對照 [Source of Truth](/backend/knowledge-cards/source-of-truth/)。

## 可觀察訊號與例子

系統需要 database 設計的訊號是資料要被長期保存、查詢、修改與稽核。訂單服務需要保存訂單狀態、付款紀錄、出貨狀態與取消原因；這些資料會影響客服、帳務、出貨與報表。

## 判斷條件與後果

Database 承擔服務的正式狀態，設計時漏掉的項目在不同時間點變成代價。沒有 [schema migration](/backend/knowledge-cards/schema-migration/) 的流程時，欄位變更只能停機或手動執行；[transaction boundary](/backend/knowledge-cards/transaction-boundary/) 與 [isolation level](/backend/knowledge-cards/isolation-level/) 沒有定義時，兩個同時修改同一張訂單的請求，結果取決於誰先寫入；[connection pool](/backend/knowledge-cards/connection-pool/) 沒有上限時，連線用盡，新請求排隊或直接失敗。備份回復沒有演練過時，資料損毀當下才知道還原是否可行；權限與資料保留沒有定義時，每個服務都改得了每一張表，資料也不會被刪。query latency、lock、[replication lag](/backend/knowledge-cards/replication-lag/)、connection pool 使用量與錯誤分類沒有觀測時，延遲上升分不出是慢查詢、鎖等待、讀到落後的 replica，還是連線排隊。
