---
title: "3.4 consumer 設計與去重"
date: 2026-04-23
description: "整理 consumer、checkpoint 與 replay safety"
weight: 4
tags: ["backend", "message-queue", "consumer"]
---

消費者設計（consumer design）的核心責任是把訊息投遞結果轉成可恢復的業務結果。queue 層提供 delivery 保證，consumer 層提供 processing 與 recovery 保證；三者對齊後，非同步流程才具備可預期性。

## 三層語意

consumer 端需要同時處理三層語意：

1. delivery semantics：訊息是否被成功投遞與確認，包含 ack/nack、retry、DLQ。
2. processing semantics：業務副作用是否可承受重複、亂序與部分失敗。
3. recovery semantics：故障後是否能重播、補償與回復到一致狀態。

這三層拆開後，才能看清問題落在哪一層。訊息送達不代表副作用完成；副作用完成不代表系統可恢復。

## consumer group、partition 與順序責任

[consumer group](/backend/knowledge-cards/consumer-group/) 與 [partition](/backend/knowledge-cards/partition/) 定義了並行與順序邊界。順序要求高的流程要把同一鍵值固定在同一 partition；吞吐優先的流程可提高 partition 數並分散處理。

分區策略會直接影響恢復成本。分區鍵混亂時，重播與補償很難限定範圍，事故期間容易擴大影響面。

## checkpoint、offset 與 idempotency

[checkpoint](/backend/knowledge-cards/checkpoint/) 與 [offset](/backend/knowledge-cards/offset/) 的責任是標記「處理到哪裡」，不是「業務一定完成」。寫 checkpoint 的時機要晚於副作用提交，避免進度前移導致資料遺漏。

[idempotency](/backend/knowledge-cards/idempotency/) key 的責任是讓重試與重播可重入。付款、發票、通知、庫存變更都需要明確冪等鍵與去重儲存策略，讓「至少一次投遞」不會變成「多次業務結果」。

## replay safety

replay safety 的核心是先定義可重播範圍，再定義副作用控制。常見做法包含：

1. 限定 replay window，避免一次重播跨越多個版本邊界。
2. 將副作用拆成可比對與可補償動作，保留對帳路徑。
3. 對 replay 期間的下游壓力設置節流與停損條件。

poison message 要獨立隔離。持續重試同一壞訊息會壓垮整體吞吐，穩定做法是送入 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)，再走診斷與修復流程。

## 判讀訊號

| 訊號                                                            | 判讀重點                         | 對應動作                                    |
| --------------------------------------------------------------- | -------------------------------- | ------------------------------------------- |
| [consumer lag](/backend/knowledge-cards/consumer-lag/) 持續上升 | consumer 吞吐低於輸入速率        | 提升併發、拆分 partition、檢查下游瓶頸      |
| retry count 上升且成功率下降                                    | 錯誤已從暫時性轉為系統性         | 啟動降級、切換路由、保留重播窗口            |
| duplicate side effect 增加                                      | 冪等鍵或去重流程失效             | 修正 idempotency store、暫停高風險副作用    |
| DLQ 量快速增加                                                  | payload 或版本相容性問題集中爆發 | 分批隔離、加 schema 檢查、修復後定向重播    |
| replay 期間下游 timeout 同步上升                                | 重播速率超出依賴容量             | 節流 replay、分段回放、加 backpressure 控制 |

## 常見誤區

把 consumer 設計等同於「把 handler 寫完」，會漏掉恢復責任。consumer 的工程價值在於故障後仍可追蹤、可補償、可重播。

把 DLQ 當成終點，會讓問題在下次事件再出現。DLQ 的責任是隔離與診斷入口，最終要回到 schema、邏輯或依賴治理。

## 案例回寫

consumer 恢復語意可用 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 與 [3.C3 LinkedIn：TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/) 對照回寫。先判讀問題是 idempotency 失效、checkpoint 前移，還是 replay 邊界失控，再對應本章的 processing/recovery 段落。

若重播成功但業務狀態仍不一致，先補副作用補償與對帳路徑，並把決策證據同步到 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨模組路由

consumer 設計是 01/03/04/06/08 的交界點。

1. 與 01 的交接：交易與發布一致性回到 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) 與 [1.3 transaction boundary](/backend/01-database/transaction-boundary/)。
2. 與 04 的交接：lag、retry、DLQ、duplicate 指標進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
3. 與 06 的交接：重試與重播驗證進入 [6.12 Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/)。
4. 與 08 的交接：pause consumer、replay 決策與補償判斷記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要先建立 broker 層投遞模型，接著讀 [3.1 broker 基礎與投遞模型](/backend/03-message-queue/broker-basics/) 與 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。要看錯誤切換案例，接著讀 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。
