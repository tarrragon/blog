---
title: "Transaction"
date: 2026-04-23
description: "說明 transaction 如何讓一組資料變更一起成功或一起回復"
weight: 138
---

Transaction 的核心概念是「把一組資料變更包成同一個一致性單位」。在 [transaction boundary](/backend/knowledge-cards/transaction-boundary/) 內，[database](/backend/knowledge-cards/database/) 會依 [isolation level](/backend/knowledge-cards/isolation-level/) 保護讀寫，並在 commit 或 rollback 時決定這組變更的結果。

## 跟其他概念的關係

Transaction 是正式資料一致性的工具。它適合保護同一個 database 內的狀態變更，例如建立訂單、扣庫存、寫入付款紀錄；跨服務通知、外部 API 與 [broker](/backend/knowledge-cards/broker/) publish 則需要 [outbox pattern](/backend/knowledge-cards/outbox-pattern/)、補償或 [data reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 可觀察訊號與例子

系統需要 transaction 的訊號是半完成狀態會造成產品錯誤。付款紀錄建立成功但訂單仍停在未付款，客服、倉儲與帳務會看到衝突資料；transaction 可以把這些同庫變更合併成同一個成功條件。

## 判斷條件與後果

Transaction 的範圍與持續時間決定它佔住資源多久。交易範圍裡包含外部 API 呼叫或長時間計算時，這段期間取得的 lock 與從 [connection pool](/backend/knowledge-cards/connection-pool/) 借出的連線都不會釋放，其他請求排隊等鎖或等連線，尖峰時整個服務的延遲跟著上升，原因是 database 要到 commit 或 rollback 才放掉鎖與連線。交易因 deadlock 或 [timeout](/backend/knowledge-cards/timeout/) 失敗時，這組變更已整組 rollback，可以依 [retry policy](/backend/knowledge-cards/retry-policy/) 整筆重跑；違反業務規則的失敗重跑幾次都得到同樣結果，所以錯誤先分類，再決定是否重試。外部呼叫與長時間工作因此放在交易範圍之外。
