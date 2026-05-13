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

## Queue 語意誤配是 broker 遷移最常見的失敗模式

Broker 遷移失敗的根因通常是 *consumer 對舊 broker 行為的隱式依賴*、不是 broker 本身效能。表面上訊息仍被送達、但業務資料開始出現重複扣款、重複寄信、狀態漏更新。

對應 [3.C9 反例：Queue Semantics Mismatch Cutover](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) — case 揭露切換後語意誤配三個方向：consumer 依賴特定 offset 行為、依賴特定重試節奏、依賴特定 idempotency 行為。失敗重播時、新系統即使提供相近 delivery semantics、結果可能不同。語意誤配會沿著下游資料寫入擴散、難以靠 queue depth 判斷。

**典型誤配場景**（基於通用 broker 行為知識展開、非 3.C9 case 原文具體列舉）：

- **At-least-once 假設變成 exactly-once 依賴**：consumer 假設 broker 僅送一次、靠記憶單次處理；新 broker 重送同一 message、consumer 處理兩次
- **Offset 跳號處理差異**：舊系統重啟後 offset 從特定位置開始、新系統可能從 latest / earliest 不同位置開始
- **Consumer group rebalance 行為差異**：rebalance 期間舊系統會 pause 處理、新系統可能繼續處理、產生並發寫入衝突
- **DLQ retry 節奏差異**：舊系統 DLQ message 預設不重試、新系統可能自動重試、製造重複副作用

**回退判讀**：回退前要先確認哪一段資料已經被新語意處理過。直接切回舊 broker 可能讓同一批事件再次被處理。穩定做法是先凍結新 consumer、保留 offset 對照與 replay 範圍、再決定補償或重播。

詳細處理 / 恢復語意分層見 [3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/)。規模差異判讀（小 / 中 / 大型服務的 job queue 治理重點）見 [3.8 queue-consumer-retry-replay-handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/) — 中型服務常見問題是 lag/DLQ 長期累積、需具備定向 replay 能力、否則退回全 topic 重播會放大下游壓力。

## 三個工程議題要一起設計

`Consumer idempotency` + `重播流程` + `下游承載能力` 三件事是 consumer design 的鐵三角、需同步落地。缺一個會在規模化時暴露成事故：

- **Consumer idempotency 不完整**：DLQ replay 後產生重複副作用、即使 broker 切換成功、業務帳本仍然錯亂
- **重播流程不完整**：事故當下需具備定向 replay 能力、否則退回全 topic 重播會放大下游壓力
- **下游承載能力不足**：consumer 跟 broker 都健康、但下游 DB / API 撐不住 replay 速率、形成新事故

Job queue 的拓樸分工是另一個獨立議題、跟鐵三角互補但不重疊 — 詳見 [3.8 Job queue 拓樸分工](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)、主寫 Slack Kafka + Redis 案例。consumer 內部三件事要做好之外、不同類工作（高吞吐 / 即時 / 持久）也應專注單一目標、其他目標拆到對應路徑。

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
這組案例主要支撐的是「處理恢復語意」判讀，不直接支撐 deployment drain 或 cache eviction；若根因在切流順序或快取容量，應轉到 5.3 或 2.3。

若重播成功但業務狀態仍不一致，先補副作用補償與對帳路徑，並把決策證據同步到 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨模組路由

consumer 設計是 01/03/04/06/08 的交界點。

1. 與 03 內部的交接：processing/recovery 語意完整定義在 [3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/)；event contract 跟 replay boundary 在 [3.7](/backend/03-message-queue/event-contract-replay-boundary/)；規模差異判讀跟 job queue 拓樸分工在 [3.8](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。
2. 與 01 的交接：交易與發布一致性回到 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) 與 [1.3 transaction boundary](/backend/01-database/transaction-boundary/)。
3. 與 04 的交接：lag、retry、DLQ、duplicate 指標進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
4. 與 06 的交接：重試與重播驗證進入 [6.12 Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/)。
5. 與 08 的交接：pause consumer、replay 決策與補償判斷記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要看 processing / recovery 三層語意完整定義、接著讀 [3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/)。要建立 broker 層投遞模型，接著讀 [3.1 broker 基礎與投遞模型](/backend/03-message-queue/broker-basics/) 與 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。要看錯誤切換案例，接著讀 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。
