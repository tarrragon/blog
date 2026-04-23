---
title: "Transaction"
date: 2026-04-23
description: "說明 transaction 如何讓一組資料變更一起成功或一起回復"
weight: 137
---

Transaction 的核心概念是「把一組資料變更包成同一個一致性單位」。在 [transaction boundary](../transaction-boundary/) 內，[database](../database/) 會依 [isolation level](../isolation-level/) 保護讀寫，並在 commit 或 rollback 時決定這組變更的結果。

## 概念位置

Transaction 是正式資料一致性的工具。它適合保護同一個 database 內的狀態變更，例如建立訂單、扣庫存、寫入付款紀錄；跨服務通知、外部 API 與 [broker](../broker/) publish 則需要 [outbox pattern](../outbox-pattern/)、補償或 [data reconciliation](../data-reconciliation/)。

## 可觀察訊號與例子

系統需要 transaction 的訊號是半完成狀態會造成產品錯誤。付款紀錄建立成功但訂單仍停在未付款，客服、倉儲與帳務會看到衝突資料；transaction 可以把這些同庫變更合併成同一個成功條件。

## 設計責任

Transaction 設計要控制範圍、時間、鎖、[retry policy](../retry-policy/)、[timeout](../timeout/) 與錯誤分類。長 transaction 會增加 lock 與 [connection pool](../connection-pool/) 壓力，因此應把外部呼叫與長時間工作移出交易範圍。
