---
title: "Containment"
tags: ["事故圍堵", "Containment"]
date: 2026-04-24
description: "說明事故處理中如何限制擴散面，為回復與驗證爭取時間"
weight: 267
---


Containment 的核心概念是「在事故期間限制風險擴散，維持可控處置空間」。它是止血、隔離與收斂節奏的上位概念。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 概念位置

Containment 位在 [incident-severity](/backend/knowledge-cards/incident-severity/)、[degradation](/backend/knowledge-cards/degradation/)、[failover](/backend/knowledge-cards/failover/) 與 [rollback-strategy](/backend/knowledge-cards/rollback-strategy/) 之間。它先回答保護邊界，再回答恢復順序。

## 可觀察訊號與例子

系統需要 containment 的訊號是影響面快速擴大、異常行為跨服務傳播、或回復決策尚未完成。常見動作包含入口隔離、權限收斂、會話失效與流量切換。

## 設計責任

containment 要定義觸發條件、執行順序、停止條件與驗證關閉標準。它應該讓團隊在壓力下快速做出一致決策。
