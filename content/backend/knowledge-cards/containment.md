---
title: "Containment"
tags: ["事故圍堵", "Containment"]
date: 2026-04-24
description: "說明事故處理中如何限制擴散面，為回復與驗證爭取時間"
weight: 268
---

Containment 的核心概念是「在事故期間限制風險擴散，維持可控處置空間」。它是止血、隔離與收斂節奏的上位概念。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 跟其他概念的關係

Containment 位在 [incident-severity](/backend/knowledge-cards/incident-severity/)、[degradation](/backend/knowledge-cards/degradation/)、[failover](/backend/knowledge-cards/failover/) 與 [rollback-strategy](/backend/knowledge-cards/rollback-strategy/) 之間。它先回答保護邊界，再回答恢復順序。

## 可觀察訊號與例子

系統需要 containment 的訊號是影響面快速擴大、異常行為跨服務傳播、或回復決策尚未完成。常見動作包含入口隔離、權限收斂、會話失效與流量切換。

## 判斷條件與後果

Containment 在事故的壓力下才啟動，事先定好的四項條件決定當下的處置是否一致。沒有觸發條件時，什麼時候隔離由當班的人臨場判斷，同樣的情況在不同人手上得到不同的處置；沒有執行順序時，入口隔離、權限收斂、會話失效與流量切換可能漏掉一項，或以每次不同的順序執行；沒有停止條件時，隔離措施在風險解除之後仍留著，持續影響正常的使用者；沒有驗證關閉的標準時，containment 宣告結束，卻說不出風險擴散是否已經停止。
