---
title: "3.1 broker 基礎與投遞模型"
date: 2026-04-23
description: "先理解 broker、queue、consumer 與 delivery semantics"
weight: 1
tags: ["backend", "message-queue", "broker"]
---

這一章先建立訊息佇列的基本模型，後面的 [durable queue](/backend/knowledge-cards/durable-queue/)、outbox 與 [consumer](/backend/knowledge-cards/consumer/) 設計都會建立在這些語意上。

訊息代理（broker）的核心責任是解耦 producer 與 consumer，讓非同步工作具備可排隊、可重試、可隔離的傳遞路徑。它定位在傳遞與協調層。

## broker 跟 protocol 是兩個獨立的軸

Broker 是訊息分發的具體實作產品（RabbitMQ、Kafka、NATS、EMQX）、protocol 是訊息交換的線路規格（AMQP、MQTT、STOMP、Kafka wire protocol）。兩個軸獨立、形成多對多關係：

- 一個 broker 可實作多個 protocol：RabbitMQ 主走 AMQP、透過 plugin 也支援 MQTT 跟 STOMP；NATS 主走自家 protocol、JetStream 額外提供 KV 與 Object Store API
- 一個 protocol 可被多個 broker 實作：MQTT 由 EMQX / HiveMQ / Mosquitto / RabbitMQ MQTT plugin 各自實作；AMQP 主要是 RabbitMQ 跟 Apache Qpid

選型討論時要分清「我需要的是 protocol（如 device 端要 MQTT 因為輕量 / IoT 標準）」還是「broker 產品（如 RabbitMQ vs EMQX 的運維 / 生態取捨）」。當 protocol 跟 broker 都需要、會出現 protocol 橋接場景 — 例：device 端透過 MQTT 連 RabbitMQ MQTT plugin、broker 內部把 MQTT topic 自動映射成 AMQP routing key、AMQP-side consumer 用 routing key 訂閱。

這層分離也影響故障判讀：device 連不上是 protocol 層問題、broker 之間 routing 錯是 broker 內部 plugin / mapping 問題、consumer 收不到是 AMQP binding 問題 — 三層各自獨立、不能混為一談。

## broker、queue、consumer 的分工

[broker](/backend/knowledge-cards/broker/) 管理訊息儲存、分發與確認流程；queue 或 topic 承載傳遞單位；consumer 承擔業務處理。分工清楚後，故障判讀才能定位在正確層級：投遞故障、消費故障或下游依賴故障。

producer 發送成功只代表 broker 已接收，不代表業務結果完成。業務完成需要 consumer 提交副作用並確認進度。

## push 與 pull 模型

push 模型由 broker 主動推送訊息，適合低延遲場景；pull 模型由 consumer 主動拉取，適合吞吐控制與批次處理。實務上常結合使用：broker 管理可見性與重試，consumer 控制節流與併發。

模型選擇重點是背壓控制。當下游變慢時，系統是否能限制消費速率並保留恢復空間，是穩定性的關鍵。

## 傳遞語意（delivery semantics）

三種常見 delivery semantics：

1. at-most-once：可能丟失，不重送，低延遲低成本。
2. at-least-once：可能重複，需冪等保護，最常見實務語意。
3. exactly-once：語意成本高，通常在特定邊界內成立，需要嚴格協議與系統支持。

實務上多數後端系統採 at-least-once，再用 consumer 去重與補償達到業務可接受結果。

## ack / nack 流程

[ack/nack](/backend/knowledge-cards/ack-nack/) 是 delivery 控制點。ack 代表該訊息可從待處理集合移除；nack 代表稍後重試或分流。ack 時機過早會造成資料遺失，過晚會造成重複處理與堆積。

穩定流程是：完成核心副作用後再 ack，暫時故障走受控重試，持續故障走 DLQ 隔離。

## 語意保證的不同實作機制

同一層 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)、不同 broker 用不同協議機制達成。讀懂 broker 行為的關鍵、是辨認「at-least-once」這個語意承諾、底下是哪種具體機制負責 — 故障訊號跟操作旋鈕跟著不同。

三種常見實作機制：

| 機制                 | 代表 broker         | 達成方式                                               | 主要操作旋鈕                                       |
| -------------------- | ------------------- | ------------------------------------------------------ | -------------------------------------------------- |
| QoS handshake        | MQTT 系列           | client 與 broker 之間的多次握手（QoS 0 / 1 / 2）       | QoS 等級、session persistence、retained message    |
| Broker ACK + retry   | RabbitMQ、SQS、NATS | consumer 處理後回 ack、未 ack 由 broker 重新投遞       | ack / visibility timeout、prefetch、DLQ            |
| Replication + commit | Kafka、Pulsar       | producer 寫入後等待 replica commit、consumer 用 offset | acks 等級（0 / 1 / all）、min.insync.replicas、ISR |

三個機制的工程含義不同。QoS handshake 把可靠性責任拉到 wire protocol 層、適合 device-to-broker 場景但 broker-to-consumer 還要另外處理；broker ACK 把責任放在 consumer 處理完才確認、適合「處理即承諾」的任務隊列；replication 把責任放在訊息已被多份保存、適合「寫入即承諾」的事件流。

### 機制差異的故障訊號

機制決定故障表現。同樣是「訊息重複投遞」、不同機制要看不同訊號：

- QoS handshake：QoS 1 重傳是設計、QoS 2 重傳代表握手失敗 — 看 broker 端的 PUBREL / PUBCOMP 完成率
- Broker ACK：ack timeout 觸發 redelivery 是設計、頻繁 redelivery 代表 consumer 處理慢或下游卡 — 看 consumer 處理時間 vs ack timeout、視訊號為 [backpressure](/backend/knowledge-cards/backpressure/)
- Replication：producer retry 觸發 duplicate 是設計、ISR shrink 代表 broker 副本不穩 — 看 ISR 狀態 vs producer acks 設定

### 機制差異的操作旋鈕

挑 broker 等同於挑「可調的旋鈕集合」。把「業務需要的語意」轉成「實際要調的旋鈕」、是 broker 選型落地的關鍵步驟：

- 想保證「不丟」用 MQTT：QoS 等級提到 2、開 session persistence
- 想保證「不丟」用 RabbitMQ：consumer 走 manual ack、配 [DLQ](/backend/knowledge-cards/dead-letter-queue/)、設 prefetch 限併發
- 想保證「不丟」用 Kafka：producer acks=all、min.insync.replicas ≥ 2、consumer commit-after-process

機制不同、可調旋鈕不同、operator 要熟悉的訊號也不同。這是「broker 系統複雜度」的真實來源 — 不是「broker 難安裝」、而是「broker 旋鈕集合的學習與調校曲線」。

## 判讀訊號

| 訊號                            | 判讀重點                       | 對應動作                       |
| ------------------------------- | ------------------------------ | ------------------------------ |
| producer 發送成功但業務結果缺漏 | 投遞成功與處理成功語意混淆     | 補 consumer 確認與結果對帳     |
| queue depth 穩定但延遲持續上升  | 消費速率不足或重試佔用主通道   | 分離重試隊列、調整併發與節流   |
| ack 成功率高但 duplicate 增加   | ack 時機與副作用提交順序不對齊 | 延後 ack、補 idempotency       |
| nack 事件集中在同類訊息         | payload 或下游契約失配         | 分流到 DLQ、修復契約後定向重播 |
| 消費重啟後堆積迅速擴大          | 背壓與可見性控制不足           | 限制拉取窗口、調整重試間隔     |

## 常見誤區

把 broker 當成保證業務正確性的元件，會把消費責任與補償責任遺漏。broker 保證傳遞語意，業務正確性要由 consumer 設計承擔。

把 exactly-once 當成預設目標，也容易過度設計。先定義可接受失敗代價，再選擇對應語意，通常更符合實務。

## Broker 規模化的角色變化

Broker 在規模化服務承擔的責任從「單隊列工具」轉到「平台治理問題」— 容量規劃焦點從擴 broker 變成多租戶隔離、配額管理、跨團隊觀測標準化。

對應 [3.C6 Uber Kafka Infrastructure Evolution](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/) — Uber 事件平台服務眾多團隊、focus 從 broker 容量是否充足轉到 team 之間的隔離邊界。對應 [3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/) — 規模化必然分層 cluster、按業務特性跟可靠性需求分配不同叢集、高優先 workload 跟低優先 workload 各自獨立。

**規模化的三個角色階段**（依據 3.C6 / 3.C4 / 早期服務對照、整理出三個典型階段）：

- **單隊列工具**（規模尚小階段）：一個 Kafka cluster、所有 service 共用、broker 擴容是主要工作、團隊各自管理自己的 topic
- **多租戶平台**（中大型階段）：跨團隊共用 cluster、平台 team 設定 quota、topic 命名規範、容量配額、觀測標準。3.C6 描述 Uber 在這階段「標準化 topic 治理與故障處理流程」、把跨團隊運維責任收斂到平台層
- **分層治理平台**（規模化階段）：不同業務特性走不同 cluster（critical / standard / experimental）、跨 cluster 路由跟治理變主要工作。3.C4 描述 LinkedIn「依流量與可靠性需求分層」、高優先 workload 提供獨立保護

判讀含義：當 broker incident 影響多個 team 不相關業務、屬於該分層的訊號。規模化後焦點要轉向跨 team 隔離跟跨 cluster 治理、單純擴 broker 處理不了多租戶共擠的結構性問題。攻擊面跟控制面見 [3.5 紅隊章 Multi-tenant broker 隔離邊界](/backend/03-message-queue/red-team-delivery-layer/)。

## Queue 變跨區關鍵路徑的特殊挑戰

當 queue 變成跨區關鍵路徑（payment、order、notification 都靠它）、容量規劃焦點從 throughput 變成 *discoverability* 跟 *routing freshness*。

對應 [3.C1 Meta FOQS](/backend/03-message-queue/cases/meta-foqs-global-migration/) — FOQS 從區域升級到全域、目標是讓災害期間 queue 仍可被存取、控制遷移期間的延遲跟可用性風險。Focus 從 queue 吞吐量轉到災害時的 broker 可達性、routing 狀態新鮮度、tenant 遷移節奏。

**跨區 queue 的設計挑戰**：

- **Discoverability**：client 在 region failover 後需透過 service discovery + DNS / health check 動態解析 broker endpoint、找到新 primary broker
- **Routing freshness**：broker topology 變更後、client 多久能拿到新 routing 表、stale routing 期間 message 流向錯 broker、要設定 routing TTL + 主動 refresh
- **Tenant 遷移節奏**：規模化跨區 queue 採分批 cutover、保留 client 連續性
- **Stale routing 補貨延遲治理**：routing 過時造成 message 累積在錯誤 broker、要設定 timeout + 重新發現機制、讓 client 重新發現新 broker 並切換到健康路徑

## 案例回寫

投遞語意可用 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 做回寫。先判讀事件是 delivery 層失配，還是 processing/recovery 層失配，再回到本章檢查 ack 時機、重試節奏與隔離策略是否清楚。
這個案例主要支撐的是「語意分層與投遞責任」判讀，不直接支撐資料庫 schema 演進或 LB timeout；若問題在資料模型或連線生命週期，應轉到 1.2 或 5.3。

若投遞成功但業務結果缺漏，先補齊語意分層，再分別回寫 [3.2 durable queue](/backend/03-message-queue/durable-queue/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 跨模組路由

1. 與 3.2 的交接：持久化與重試節奏回到 [durable queue 與重試策略](/backend/03-message-queue/durable-queue/)。
2. 與 3.4 的交接：消費恢復與去重回到 [consumer 設計與去重](/backend/03-message-queue/consumer-design/)。
3. 與 4.20 的交接：投遞與消費訊號納入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
4. 與 6.12 的交接：重播與冪等驗證回到 [Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/)。

## 下一步路由

要進一步處理持久化與重試控制，接著讀 [3.2 durable queue 與重試策略](/backend/03-message-queue/durable-queue/)。要處理交易與發佈一致性，接著讀 [3.3 outbox pattern 與發佈一致性](/backend/03-message-queue/outbox-pattern/)。
