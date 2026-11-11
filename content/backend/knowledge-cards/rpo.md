---
title: "RPO"
tags: ["復原點目標", "RPO"]
date: 2026-04-23
description: "說明恢復點目標如何定義可接受資料損失範圍"
weight: 160
---

RPO 的核心概念是「事故後可接受的最大資料損失窗口」。它回答回復後最多能遺失多久的資料變更。 可先對照 [Database](/backend/knowledge-cards/database/)。

## 跟其他概念的關係

RPO 與 [database](/backend/knowledge-cards/database/)、備份策略、[replication lag](/backend/knowledge-cards/replication-lag/) 與 [data reconciliation](/backend/knowledge-cards/data-reconciliation/) 緊密相關。RPO 越嚴格，資料保護與同步成本通常越高。

## 可觀察訊號與例子

系統需要 RPO 的訊號是資料遺失會造成財務或合規風險。訂單與付款資料若目標 RPO 接近零，需要更嚴格的持久化與回復設計。

## 判斷條件與後果

RPO 的判斷對象是每一類資料能承受遺失多久的變更，以及保護機制實際做得到多少。所有資料用同一個 RPO 時，對訂單與付款太寬就留下財務或合規風險，對可以從其他來源重建的資料（快取、衍生的報表）太嚴就付出不必要的同步成本，所以 RPO 依資料類型分級。保護機制（備份頻率、replication）給的是理論上的遺失窗口；備份檔損壞或 replication lag 超出預期時，實際窗口比設定的長，只有備份回復演練量得出實際能回到哪個時間點。演練量到的窗口比設定的長時，這類資料進入例外處理：補強保護機制，或把承諾改成實際量到的窗口。
