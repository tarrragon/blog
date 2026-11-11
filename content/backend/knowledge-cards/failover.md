---
title: "Failover"
tags: ["容錯切換", "Failover"]
date: 2026-04-23
description: "說明主要服務或節點失效時如何切換到備援能力"
weight: 31
---

Failover 的核心概念是「主要路徑失效時切換到備援路徑」。備援可以是另一個 instance、另一個 availability zone、另一個資料庫 replica、另一個服務供應商或簡化功能。 可先對照 [Fallback Plan](/backend/knowledge-cards/fallback-plan/)。

## 跟其他概念的關係

Failover 是可用性設計的一部分。它要處理健康判斷、切換觸發、資料一致性、DNS 或 load balancer 更新、連線重建與回切流程。 可先對照 [Fallback Plan](/backend/knowledge-cards/fallback-plan/)。

## 可觀察訊號與例子

系統需要 failover 的訊號是單一節點、單一區域或單一供應商故障會造成停機。付款服務可以在主要供應商中斷時切到備援供應商，但要處理交易查詢、費率、風控與對帳差異。

## 判斷條件與後果

Failover 由機器自動觸發還是由人決定，誤判造成的代價不同。自動 failover 的健康訊號太寬鬆時，一次短暫的網路抖動就觸發切換，主要路徑仍然正常時備援就接手，切換本身帶來連線重建與資料一致性的風險；人工 failover 的決策權限不清楚時，主要路徑已經失效，切換卻停在等人決定。兩種方式都需要 runbook：沒有資料檢查時，備援可能帶著落後的 replica 資料接手；沒有回切條件時，主要路徑恢復之後何時切回只能當場判斷；沒有按頻率演練時，切換步驟要到實際故障時才第一次被執行，DNS 或 load balancer 更新、交易查詢與對帳差異這些環節是否走得通都是未知。
