---
title: "Saga"
date: 2026-05-27
description: "說明跨服務的長事務如何用一系列補償型 transaction 達成業務一致性"
weight: 27
---

Saga 是處理跨服務分散事務的設計模式：把一筆業務動作拆成一系列局部 transaction、每個 step 在對應服務內以本地 [transaction](/backend/knowledge-cards/transaction/) 完成、若中途某 step 失敗、就反向執行已完成 step 的補償 transaction 回到一致狀態。Saga 不提供 ACID 的 atomic 保證、是用「最終一致」+「補償可回退」換取跨服務獨立性。

## 概念位置

Saga 處於跨服務分散事務的設計層、跟 [outbox pattern](/backend/knowledge-cards/outbox-pattern/)、[idempotency](/backend/knowledge-cards/idempotency/) 一起構成 microservice 一致性的三件套。Saga 解「跨服務事務一致」、outbox 解「事件不丟」、idempotency 解「補償可重放」。

兩種常見的 saga 實作：

- **Choreography（編舞）**：每個服務監聽事件、自行決定下一步動作、不需要中央協調者。優點是耦合低；缺點是業務流程散落、debug 困難。
- **Orchestration（編排）**：用一個中央 saga orchestrator 持有 state machine、逐步呼叫各服務並追蹤狀態。優點是流程集中可見；缺點是 orchestrator 本身成為單點。

Saga 的核心責任邊界：補償 transaction 必須是 idempotent（同一補償可重複執行不出錯），因為 saga 引擎在故障重試時會重放。沒有 idempotent 設計、saga 補償會變成新的事故來源。

Saga 跟 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 經常一起出現：outbox 保證「事件不丟」、saga 保證「跨服務一致」。兩者組合是 microservice 分散事務的事實標準。
