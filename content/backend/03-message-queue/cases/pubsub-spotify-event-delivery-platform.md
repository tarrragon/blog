---
title: "3.C60 Spotify：Event Delivery 從 Kafka 遷到 Pub/Sub"
date: 2026-05-18
description: "Spotify 全球 event delivery 從 Kafka 遷到 Pub/Sub、~2500 VM、Q1 2019 8M events/s、350TB/day raw、自建 dedup。"
weight: 60
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

Spotify 把全球 event delivery 從 Kafka 遷到 Cloud Pub/Sub 的案例揭露了大規模 pull subscription 的工程現實 — at-least-once 語意意味著應用層去重不可省。

## 業務背景

Spotify 的 Event Delivery 系統負責把所有使用者行為事件（播放、搜尋、推薦互動、廣告曝光）從客戶端經由資料管線送到下游消費者。事件是推薦引擎、A/B test、廣告計費跟 analytics 的核心輸入。

遷移到 GCP Pub/Sub 後的系統規模：每個 event type 一個 topic、~15 個 microservice 跑在 ~2500 VM 上、Q1 2019 高峰 8M events/sec、每日 350 TB raw event 流量。遷出 Kafka 的動機跟技術評估見 [3.C20 Spotify 遷出 Kafka（反例）](/backend/03-message-queue/cases/kafka-spotify-event-delivery-exodus/)。

## 技術挑戰

### At-least-once 語意下的重複

Cloud Pub/Sub（早期版本）提供 at-least-once delivery — 同一筆訊息可能被 deliver 多次。在每日 350 TB 的流量下，「偶爾重複」的頻率足以影響 analytics 數據跟廣告計費的準確性。

Pub/Sub 的重複來源有兩個：ack deadline 到期前 consumer 還沒處理完、訊息被重新 deliver 給其他 consumer；以及 Pub/Sub backend 的內部 redelivery（罕見但非零）。

### Pull subscription 的流控

Pull subscription 讓 consumer 主動從 Pub/Sub 拉取訊息（vs push subscription 由 Pub/Sub 推送到 HTTP endpoint）。Pull 的好處是 consumer 可以控制自己的消費速度，避免被推送壓垮。

大規模 pull subscription 的挑戰在於流控的精細度 — 每個 consumer VM 要設定合理的 maxOutstandingMessages 跟 maxOutstandingBytes，太大會讓 consumer 記憶體不足、太小會浪費 Pub/Sub 的吞吐能力。Spotify 的 2500 VM 各自獨立做 pull，需要在 fleet 級別保持流控的一致性。

### 每個 event type 一個 topic 的治理

Spotify 按 event type 建立 topic（例如 `play-event`、`search-event`、`ad-impression`）。Event type 數量成長後，topic 數量跟著增長。每個 topic 需要獨立的 subscription、monitoring、ack deadline 設定跟 retention policy。

Topic 治理的工程問題是「誰 own 這個 topic、schema 變更怎麼協調、retention 該設多久」。Spotify 自建了 event delivery 平台層（Event Delivery Platform）來管理 topic lifecycle — 包括 topic 建立 / 刪除的 self-service API、schema registry、consumer group 管理。

## 解法與取捨

### 自建 deduplication 層

Spotify 在 consumer 端自建去重機制。每筆 event 帶 unique event ID，consumer 在處理前查 dedup store（記憶體 + 外部 cache）確認是否已處理過。已處理的 event 直接 ack、跳過處理邏輯。

Dedup store 的挑戰是大小跟 TTL — 要記住多久以前的 event ID 才夠。TTL 太短會漏掉 late redelivery（Pub/Sub 在 ack deadline 之後才重新 deliver）、TTL 太長 dedup store 太大。Spotify 用滑動視窗（retention 跟 ack deadline 的倍數）設定 TTL。

### 取捨

| 面向                  | Pub/Sub + 自建 dedup         | 自管 Kafka 0.8+                   |
| --------------------- | ---------------------------- | --------------------------------- |
| 運維成本              | 低（Pub/Sub 全託管）         | 高（自管 broker × 多 region）     |
| 語意保證              | At-least-once + 應用層 dedup | At-least-once（idempotent 0.11+） |
| 跨 region replication | 原生支援                     | 需要 MirrorMaker 或自建           |
| 流控精細度            | Pull subscription 可控       | Consumer group 自動分配           |
| Topic 治理            | 需要自建平台層               | Kafka 生態工具（Confluent 等）    |
| Dedup 成本            | 額外的 cache / store 成本    | Idempotent producer 減少需求      |

自建 dedup 的成本是 Spotify 選 Pub/Sub 的額外付出。這個代價在託管方案的運維節省面前被接受 — 維護一個 dedup cache 的成本遠低於維護跨 5 個 datacenter 的 Kafka broker fleet。

## 回寫教材的連結

- [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/)：push vs pull subscription、ack deadline、ordering 跟 DLT 的進階主題
- [3.C20 Spotify 遷出 Kafka](/backend/03-message-queue/cases/kafka-spotify-event-delivery-exodus/)：遷出 Kafka 的動機跟決策判準
- [3.6 processing recovery semantics](/backend/03-message-queue/processing-recovery-semantics/)：at-least-once 語意下的 dedup 策略
- [3.7 event contract replay boundary](/backend/03-message-queue/event-contract-replay-boundary/)：event schema 跟 topic lifecycle 的治理

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 使用 GCP Pub/Sub 且下游消費者偶爾處理到重複事件
- Pull subscription 的 consumer 記憶體使用不穩定、maxOutstandingMessages 設定不合理
- Topic 數量持續增長但缺少統一的 lifecycle 管理
- 從自管 Kafka 遷移到 GCP Pub/Sub 的評估階段

## 引用源

- [Spotify's Event Delivery — Life in the Cloud](https://engineering.atspotify.com/2019/11/spotifys-event-delivery-life-in-the-cloud)
