---
title: "RPO"
tags: ["復原點目標", "RPO"]
date: 2026-04-23
description: "說明恢復點目標如何定義可接受資料損失範圍"
weight: 159
---


RPO 的核心概念是「事故後可接受的最大資料損失窗口」。它回答回復後最多能遺失多久的資料變更。 可先對照 [Database](/backend/knowledge-cards/database/)。

## 概念位置

RPO 與 [database](/backend/knowledge-cards/database/)、備份策略、[replication lag](/backend/knowledge-cards/replication-lag/) 與 [data reconciliation](/backend/knowledge-cards/data-reconciliation/) 緊密相關。RPO 越嚴格，資料保護與同步成本通常越高。

## 可觀察訊號與例子

系統需要 RPO 的訊號是資料遺失會造成財務或合規風險。訂單與付款資料若目標 RPO 接近零，需要更嚴格的持久化與回復設計。

## 設計責任

RPO 要定義資料類型分級、保護機制、驗證流程與例外處理。設定後應透過備份回復演練檢查實際可達成範圍。
