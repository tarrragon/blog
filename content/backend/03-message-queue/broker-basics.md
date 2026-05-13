---
title: "3.1 broker 基礎與投遞模型"
date: 2026-04-23
description: "先理解 broker、queue、consumer 與 delivery semantics"
weight: 1
tags: ["backend", "message-queue", "broker"]
---

這一章先建立訊息佇列的基本模型，後面的 [durable queue](/backend/knowledge-cards/durable-queue/)、outbox 與 [consumer](/backend/knowledge-cards/consumer/) 設計都會建立在這些語意上。

訊息代理（broker）的核心責任是解耦 producer 與 consumer，讓非同步工作具備可排隊、可重試、可隔離的傳遞路徑。它定位在傳遞與協調層。

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
