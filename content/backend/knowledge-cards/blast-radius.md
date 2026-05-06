---
title: "Blast Radius"
tags: ["影響半徑", "Blast Radius"]
date: 2026-04-23
description: "說明事故影響面如何估算與隔離"
weight: 154
---


Blast radius 的核心概念是「估算故障可擴散到哪些服務、資料與使用者」。它幫助團隊在事故早期決定先隔離哪個邊界，避免影響持續擴大。 可先對照 [Degradation](/backend/knowledge-cards/degradation/)。

## 概念位置

Blast radius 與 [degradation](/backend/knowledge-cards/degradation/)、[failover](/backend/knowledge-cards/failover/) 與 [rollback-strategy](/backend/knowledge-cards/rollback-strategy/) 密切相關。影響面判斷會直接改變事故分級與處置策略。

## 可觀察訊號與例子

系統需要 blast radius 判斷的訊號是單點異常開始波及更多路徑。某個推薦服務超時最初只影響商品頁，若重試策略失控，可能進一步拖慢共用 database 與 checkout 路徑。

## 設計責任

影響面設計要標出依賴拓撲、共享資源與隔離手段。事故期間應持續更新影響面估算，並把結果同步到指揮與通訊流程。
