---
title: "3.7 Event Contract 與 Replay Boundary"
date: 2026-05-11
description: "說明 event schema、idempotency key、replay window 與補償如何先於 broker 選型。"
weight: 7
tags: ["backend", "message-queue", "event-contract", "replay"]
---

Event contract 與 replay boundary 的核心責任是讓事件在版本演進、重試與重播時仍可被理解與驗證。進入具體 broker 前，讀者需要先知道事件 payload 是跨服務副作用的契約。

## Event Contract

Event contract 的責任是定義 producer 發出的事實、consumer 能依賴的欄位，以及版本演進時的相容窗口。最小 contract 包含 event id、schema version、occurred time、producer、entity id、dedup key 與資料保護範圍。

event id 讓訊息可追蹤；schema version 讓版本演進可判斷；occurred time 讓 replay 可分時間窗；dedup key 讓 consumer 可去重；PII scope 讓事件能接到資料保護。

event id 支撐 incident timeline 與重複投遞判讀。schema version 支撐新舊 consumer 共存。occurred time 支撐 replay window 與對帳查詢。dedup key 支撐 idempotency。PII scope 支撐 audit 與資料保護。這些欄位先成立，broker retention 或 partition 設計才有可依附的語意。

## Schema Compatibility

[Schema compatibility](/backend/knowledge-cards/event-schema-compatibility/) 的責任是讓 producer 與 consumer 可以分批升級。新增欄位要保留 optional，移除欄位要有相容窗口，語意改變要用新 version 或新 event type。

序列化能解析是相容性的第一層。若欄位仍存在但語意改變，consumer 仍可能產生錯誤副作用。這類變更需要在 release gate 中驗證。

## Replay Boundary

Replay boundary 的責任是限制重播範圍，避免修復動作擴大事故。Replay 要能指定 time range、tenant、partition、event type、schema version 與 downstream capacity。

replay window 要和 [time range](/backend/knowledge-cards/time-range/) 與 [query link](/backend/knowledge-cards/query-link/) 對齊，讓事後能回放當時重播的是哪一批事件。

## Compensation

Compensation 的責任是處理副作用已經發生但結果不正確的情況。寄信、發票、付款通知與 webhook 都可能需要補償，重播是其中一種恢復方式。

補償前要先判斷副作用是否可逆、是否會通知使用者、是否需要人工審核。不可逆副作用要比可重播副作用更早接到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 跨 broker 業務語意對映

跨 broker migration 的工程責任是維持業務語意對映、broker 吞吐是次要驗證項。同一份 event contract 在 Kafka、Pub/Sub、SQS、NATS 的對映概念不同、需要逐項校準。

對應 [9.C9 Spotify Kafka → Pub/Sub Migration](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) — Spotify 7500 萬用戶事件交付系統遷移、case 明確點出 Kafka 的 partition / offset / consumer group 對映成 Pub/Sub 的 subscription / ordering key / message attribute、需要校準業務語意而非直接搬。

**典型概念對映差異**（依據 9.C9 case 列出的三組對映展開、Pub/Sub 實際 API 細節為文章補充）：

- **Partition (Kafka) 跟 Subscription (Pub/Sub)**：Kafka partition 是物理分片 + 順序邊界；Pub/Sub subscription 是邏輯 fan-out、無物理分片概念。靠 Kafka partition 保證 per-key 順序的 consumer、遷到 Pub/Sub 改用 ordering key
- **Offset (Kafka) 對映成 message attribute (Pub/Sub)**：9.C9 case 原文對映方向；replay 模型差異上、Kafka offset 是位置指標、可任意回放到某個 offset；Pub/Sub 用 Snapshot + Seek API 達成類似 replay 能力、模型不同
- **Consumer Group (Kafka) 跟 Subscription (Pub/Sub)**：Kafka consumer group 內部 rebalance 自動分 partition；Pub/Sub subscription 自動分 message、語意接近但 rebalance 細節差異會影響 [in-flight](/backend/knowledge-cards/in-flight/) message 處理順序

**遷移評估要驗證的業務語意**：

- 順序保證：原系統靠 partition / consumer group 保證什麼順序、新系統能否複製
- Replay 模型：原系統 replay 方式、新系統的 replay 工具能否達成同範圍。replay window 上限由 idempotency 保留期反推、見 [3.6 Replay 跟 Idempotency 共設計](/backend/03-message-queue/processing-recovery-semantics/)
- 失敗模式：consumer 故障時、原系統的 rebalance / redelivery 行為、新系統會不會差異

判讀重點：broker migration 屬語意對映工程、吞吐能力比較是次要驗證項。對應 [3.3 outbox pattern 的「Broker 遷移階段流程」](/backend/03-message-queue/outbox-pattern/)、實作面用 dual-write + shadow consume + cutover、驗證面靠 event contract 跟 replay 邊界做對帳。

## 跨模組路由

1. 與 03 內部：replay window 跟 idempotency 共設計回到 [3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/)；broker 遷移階段流程回到 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)
2. 與 04 的交接：event contract 演進 + replay 邊界進 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
3. 與 06 的交接：event contract 跟 replay 驗證進 [6.12 Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/) 跟 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)
4. 與 07 的交接：event payload 的 PII / audit 邊界進 [7.4 data protection and masking](/backend/07-security-data-protection/data-protection-and-masking-governance/)

## 選型前判準

Broker 選型前要先回答：

1. event contract 是否能支援版本相容。
2. consumer 是否能用 dedup key 判斷重複。
3. replay window 是否能用查詢與指標證明。
4. 不可逆副作用是否有補償流程。
5. event payload 是否包含 PII 或 audit-sensitive 欄位。

這些問題決定後續要比較 broker retention、schema registry、DLQ、partition 與 replay 工具，並把吞吐放回服務語意下判讀。

## 實體服務討論承接點

實體 broker 文章要承接本篇的 event contract 與 replay boundary。Kafka 的長期 retention、RabbitMQ 的 routing 與 DLQ、SQS 的 visibility timeout、NATS JetStream 的 stream/consumer 模型，都要放回事件契約與重播邊界下判讀。

若事件需要長期 replay，後續文章要比較 retention、offset、partition 與 schema evolution。若事件主要是工作任務，後續文章要比較 visibility、ack、DLQ 與重試治理。若事件包含 PII 或高風險副作用，後續文章要比較 audit、encryption、access control 與補償流程。

## 下一步路由

要處理 outbox 與事件發布一致性，接著讀 [3.3 outbox pattern 與發佈一致性](/backend/03-message-queue/outbox-pattern/)。要處理 consumer 端去重與重播，接著讀 [3.4 consumer 設計與去重](/backend/03-message-queue/consumer-design/)。
