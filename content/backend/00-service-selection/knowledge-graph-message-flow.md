---
title: "0.9 知識網：訊息與事件決策路徑"
date: 2026-04-23
description: "把 broker、queue、ack、retry、DLQ、replay 與 idempotency 串成可操作的非同步決策語言"
weight: 9
---

非同步決策的核心原則是先定義投遞語意，再選擇傳遞工具。`queue`、`stream`、[`pub/sub`](/backend/knowledge-cards/pub-sub/)、`outbox`、`retry`、`dead-letter`、`replay` 與 `idempotency` 是同一條決策鏈，不是獨立名詞清單。

## 本章目標

學完本章後，你將能夠：

1. 用事件生命週期描述非同步需求
2. 區分「可延遲」、「可重試」、「可重播」與「可去重」的責任邊界
3. 把訊息系統術語串成可檢查的決策流程
4. 判斷目前停在概念層，還是已經進入實作層

---

## 【判讀】事件生命週期先於產品選型

事件設計的核心問題是「事件在系統裡如何出生、傳遞、處理、失敗、重試與回放」。先回答生命週期，才有辦法判斷是否要用 [broker](/backend/knowledge-cards/broker/)、[queue](/backend/knowledge-cards/queue/) 或 stream。

一條最小生命週期通常包含：

1. 產生：`producer` 何時發布事件  
   參考：[Producer](/backend/knowledge-cards/producer/) / [Outbox Pattern](/backend/knowledge-cards/outbox-pattern/)
2. 傳遞：事件放在哪種通道  
   參考：[Queue](/backend/knowledge-cards/queue/) / [Topic](/backend/knowledge-cards/topic/) / [Broker](/backend/knowledge-cards/broker/)
3. 消費：`consumer` 如何確認處理結果  
   參考：[Consumer](/backend/knowledge-cards/consumer/) / [Ack/Nack](/backend/knowledge-cards/ack-nack/)
4. 失敗：重試與隔離如何發生  
   參考：[Retry Policy](/backend/knowledge-cards/retry-policy/) / [Dead-Letter Queue](/backend/knowledge-cards/dead-letter-queue/)
5. 回復：資料如何補送與重播  
   參考：[Replay Runbook](/backend/knowledge-cards/replay-runbook/) / [Offset](/backend/knowledge-cards/offset/)

這條鏈路完整後，才進入 RabbitMQ、Kafka、Redis Streams 或雲端託管服務比較。

## 【判讀】投遞語意決定設計強度

投遞語意的核心問題是「失敗後，系統接受哪種結果」。`at-most-once`、`at-least-once` 與順序需求會直接決定重試、去重與補送成本。

接近真實網路服務的判斷方式包括：

- 通知類訊息可接受少量遺失：重點在低延遲與 [fan-out](/backend/knowledge-cards/fan-out/)。
- 金流或庫存狀態不可遺失：重點在持久化、重試與補償，並定義 [strong reliability](/backend/knowledge-cards/strong-reliability/) 路徑。
- 分析事件可接受短暫延遲：重點在可重播與批次處理。

對應卡片：

- [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)
- [Idempotency](/backend/knowledge-cards/idempotency/)
- [Message Persistence](/backend/knowledge-cards/message-persistence/)
- [Delivery Mode](/backend/knowledge-cards/delivery-mode/)

## 【判讀】壅塞與延遲要用同一組語言處理

非同步壓力的核心問題是「輸入速度高於處理速度」。這會同時反映在 [queue depth](/backend/knowledge-cards/queue-depth/)、[consumer lag](/backend/knowledge-cards/consumer-lag/)、[timeout](/backend/knowledge-cards/timeout/) 與重試風暴。

對應卡片關係：

- 壓力來源：  
  [Backpressure](/backend/knowledge-cards/backpressure/) / [Queue Depth](/backend/knowledge-cards/queue-depth/) / [Consumer Lag](/backend/knowledge-cards/consumer-lag/)
- 保護策略：  
  [Rate Limit](/backend/knowledge-cards/rate-limit/) / [Load Shedding](/backend/knowledge-cards/load-shedding/) / [Circuit Breaker](/backend/knowledge-cards/circuit-breaker/)
- 失敗擴散：  
  [Retry Storm](/backend/knowledge-cards/retry-storm/) / [Cascading Failure](/backend/knowledge-cards/cascading-failure/)

這一層討論完成前，不需要先決定 broker 產品或 [partition](/backend/knowledge-cards/partition/) 數量。

## 【判讀】回復流程是可靠性設計的一部分

回復設計的核心問題是「錯誤發生後如何回到正確狀態」。`DLQ`、`replay`、[Data Reconciliation](/backend/knowledge-cards/data-reconciliation/) 與 `runbook` 應該一起定義。

對應卡片：

- [Dead-Letter Queue](/backend/knowledge-cards/dead-letter-queue/)
- [Replay Runbook](/backend/knowledge-cards/replay-runbook/)
- [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)
- [Runbook](/backend/knowledge-cards/runbook/)

若這些概念只有名詞而沒有決策順序，系統上線後會把排障責任推給個人經驗。

## 【邊界】何時從概念章節進入實作章節

當以下問題都能回答時，代表概念層已完成，可以進入實作模組：

1. 哪些事件可遺失，哪些事件不可遺失
2. 哪些 consumer 需要去重，語意鍵是什麼
3. 何時重試、何時進 DLQ、何時啟動 replay
4. 哪些指標觸發擴容或降級

下一步建議路由：

- 進入訊息系統能力比較：[03-message-queue](/backend/03-message-queue/)
- 進入可觀測與事故流程：[04-observability](/backend/04-observability/) / [08-incident-response](/backend/08-incident-response/)
