---
title: "Saga"
date: 2026-05-27
description: "處理跨服務分散事務的補償型 transaction 序列、用最終一致換 ACID atomic"
weight: 28
---

Saga 是處理跨服務分散事務的設計模式：把一筆業務動作拆成一系列局部 [transaction](/backend/knowledge-cards/transaction/)、每個 step 在對應服務內以本地 transaction 完成、若中途某 step 失敗、就反向執行已完成 step 的補償 transaction 回到一致狀態。Saga 不提供 ACID 的 atomic 保證、是用最終一致 + 補償可回退換取跨服務獨立性。跟 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 跟 [idempotency](/backend/knowledge-cards/idempotency/) 共同構成 microservice 一致性的三件套。

## 跟其他概念的關係

Saga 處於跨服務分散事務的設計層。Saga 解「跨服務事務一致」、[outbox](/backend/knowledge-cards/outbox-pattern/) 解「事件不丟」、[idempotency](/backend/knowledge-cards/idempotency/) 解「補償可重放」。兩種常見實作 variant：

- **Choreography（編舞）**：每個服務監聽事件、自行決定下一步動作、不需要中央協調者。耦合低；業務流程散落、debug 困難。
- **Orchestration（編排）**：用一個中央 saga orchestrator 持有 state machine、逐步呼叫各服務並追蹤狀態。流程集中可見；orchestrator 是單點。

## 可觀察訊號與例子

電商 checkout 是典型 saga：下訂單 → 扣庫存 → 扣餘額 → 出貨。任一 step 失敗、反向觸發補償（退款、回滾庫存、取消訂單）。Order management、支付清算、跨服務交易都會用到。補償 transaction 失敗率非零、saga 引擎需要 retry + dead letter queue 處理。

## 判斷條件與後果

Saga 的判斷看三件事：補償能否重放、流程集中在哪裡、何時結束。saga 引擎在故障重試時會重放補償 transaction，補償不是 idempotent 時，同一筆退款或庫存回補會執行兩次，補償本身變成新的事故來源。業務流程穩定時，choreography 讓各服務只監聽事件，耦合低；流程常變或 audit 要求高時，orchestration 把 state machine 集中在 orchestrator，每一筆 saga 走到哪一步查得到，代價是 orchestrator 成為單點。saga 與每個 step 的 timeout 沒有明示時，一個 step 沒有回應會讓整筆 saga 停在中間狀態，既沒有成功也沒有補償完成，所以 timeout 要明示，到期時把 saga 推進到終態（成功或補償完成）。
