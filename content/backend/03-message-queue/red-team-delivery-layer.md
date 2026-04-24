---
title: "3.5 攻擊者視角（紅隊）：傳遞層弱點判讀"
date: 2026-04-24
description: "從重複投遞、重放濫用、毒訊息與容量壓力，盤點 message delivery 的主要弱點"
weight: 5
---

傳遞層紅隊判讀的核心目標是確認「訊息如何被重送、重放、放大與耗盡資源」。這裡的紅隊指攻擊者視角的風險檢查：先找可被放大的傳遞路徑，再回推控制面。只要系統採用 [broker](../../knowledge-cards/broker/) 或 stream，弱點就會同時落在 [delivery semantics](../../knowledge-cards/delivery-semantics/)、consumer 容量與回復流程。

## 【判讀】傳遞層弱點的主要軸線

傳遞層弱點可分成三條軸線：投遞語意、處理語意、回復語意。投遞語意看 [ack/nack](../../knowledge-cards/ack-nack/) 與重送條件；處理語意看 [idempotency](../../knowledge-cards/idempotency/) 與 side effect；回復語意看 [dead-letter queue](../../knowledge-cards/dead-letter-queue/)、[replay runbook](../../knowledge-cards/replay-runbook/) 與 [data reconciliation](../../knowledge-cards/data-reconciliation/)。

## 【可觀察訊號】何時要提高紅隊檢查優先級

下列訊號出現時，傳遞層通常需要先做弱點盤點：

- [consumer lag](../../knowledge-cards/consumer-lag/) 持續增加，且重試量同步升高
- [DLQ](../../knowledge-cards/dead-letter-queue/) 累積速度高於排空速度
- 同一事件會被多路 consumer 讀取並觸發多個下游 side effect
- 回放流程缺少操作邊界與審核節點

## 【失敗代價】傳遞層弱點的代價型態

傳遞層弱點會把局部錯誤放大成系統性壓力。重複投遞會造成重複扣款、重複通知或重複建單；毒訊息會阻塞分區與 worker；重放策略缺少邊界會把歷史事件再次推進生產流程。這些問題的共同代價是資料偏移、事故窗口延長與操作風險上升。

## 【最低控制面】進入服務實體前要先定義

傳遞層在討論具體服務前，先定義四個控制面最穩定：

1. 投遞保證模型：哪些流程接受 at-least-once、哪些流程需要更嚴格保證。
2. 去重與副作用模型：哪些操作必須具備 idempotency，如何界定重複。
3. 重試與降載模型：重試節奏、上限、退避與壓力保護機制。
4. 回復與重放模型：DLQ 分流、回放準入條件與結果校正流程。

## 【關聯卡片】

- [Poison Message](../../knowledge-cards/poison-message/)
- [Duplicate Delivery](../../knowledge-cards/duplicate-delivery/)
- [Retry Storm](../../knowledge-cards/retry-storm/)
- [Backpressure](../../knowledge-cards/backpressure/)
- [Runbook](../../knowledge-cards/runbook/)
