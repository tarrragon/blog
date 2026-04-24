---
title: "Failover"
tags: ["容錯切換", "Failover"]
date: 2026-04-23
description: "說明主要服務或節點失效時如何切換到備援能力"
weight: 30
---

Failover 的核心概念是「主要路徑失效時切換到備援路徑」。備援可以是另一個 instance、另一個 availability zone、另一個資料庫 replica、另一個服務供應商或簡化功能。

## 概念位置

Failover 是可用性設計的一部分。它要處理健康判斷、切換觸發、資料一致性、DNS 或 load balancer 更新、連線重建與回切流程。

## 可觀察訊號與例子

系統需要 failover 的訊號是單一節點、單一區域或單一供應商故障會造成停機。付款服務可以在主要供應商中斷時切到備援供應商，但要處理交易查詢、費率、風控與對帳差異。

## 設計責任

Failover runbook 要定義觸發條件、切換步驟、資料檢查、回切條件與演練頻率。自動 failover 需要更嚴格的健康訊號，人工 failover 則需要清楚的決策權限。

