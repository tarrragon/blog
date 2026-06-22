---
title: "3.C20 Spotify：Event Delivery 從 Kafka 遷出（反例）"
date: 2026-05-18
description: "Spotify Kafka 0.7 MirrorMaker best-effort 會掉資料但回報成功、broker restart 後 producer 無法恢復、決定遷到 GCP Pub/Sub。"
weight: 20
tags: ["backend", "message-queue", "case-study", "kafka"]
---

Spotify 從 Kafka 遷出到 GCP Pub/Sub 的決策揭露了兩件事：broker 的可靠性保證是版本特性而非 Kafka 的不變量；以及「升級到新版」跟「換到另一個系統」之間的決策判準。

## 業務背景

Spotify 的事件傳遞系統（Event Delivery）負責把使用者行為事件（播放、搜尋、推薦互動）從客戶端送到資料管線。系統跨 5 個 datacenter 運行 Kafka 0.7，production peak 700K events/sec、pressure test 達到 2M events/sec。事件資料是推薦系統、analytics 跟廣告計費的輸入，遺失事件直接影響商業決策的準確性。

2016 年，Spotify 決定把 Event Delivery 從 Kafka 遷移到 GCP Pub/Sub，而非升級到當時已發布的 Kafka 0.8+。

## 技術挑戰

### MirrorMaker 的 best-effort 語意

Kafka 0.7 的跨 datacenter replication 工具 MirrorMaker 在 best-effort mode 下會丟失資料但向 producer 回報成功。對 Spotify 的場景，producer 端認為事件已送達，但跨 datacenter 的 mirror 實際上丟了一部分。丟失比例在正常情況下很低，但在 broker restart 或網路抖動時可以升高到影響 analytics 準確性的程度。

這個問題的根源是 Kafka 0.7 的 producer 沒有 idempotent 保證，MirrorMaker 的 consumer offset commit 跟 producer ack 之間有 gap。

### Broker restart 後 producer 無法自動恢復

Kafka 0.7 的 producer 在 broker restart 後可能進入無法自動恢復的狀態 — 需要人工重啟 producer process。在 5 個 datacenter、數百個 producer instance 的規模下，每次 broker 維護操作都需要人工介入恢復 producer，運維成本跟 broker 數量成正比。

### 為什麼不升級到 Kafka 0.8+

Kafka 0.8 引入了 replication、新的 consumer API 跟更可靠的 producer。但 Spotify 評估後認為升級的成本接近重新部署：

- Kafka 0.7 到 0.8 的 wire protocol 不相容，需要全量遷移而非滾動升級
- 所有 producer / consumer 的 client library 都要更換
- Spotify 同時在向 GCP 遷移基礎設施，Kafka 的自管運維模式跟 GCP 的託管方向不一致

相比之下，GCP Pub/Sub 提供了託管的 exactly-once 語意、跨 region replication、零運維。遷移成本跟升級 Kafka 版本的成本相當，但遷移後的長期運維成本低得多。

## 解法與取捨

| 面向                  | 留在 Kafka（升級 0.8+）      | 遷到 GCP Pub/Sub            |
| --------------------- | ---------------------------- | --------------------------- |
| 一次性遷移成本        | 中（全量遷移、不可滾動升級） | 中（同樣需要改所有 client） |
| 長期運維成本          | 高（自管 broker × 5 DC）     | 低（託管、零 broker 維護）  |
| 可靠性保證            | 0.8+ 有 replication、改善大  | Pub/Sub 原生 exactly-once   |
| 跨 region replication | 需要自建 MirrorMaker 2.0     | 原生支援                    |
| 生態鎖定              | Kafka 生態成熟               | GCP 鎖定、跨雲成本高        |

Spotify 的判斷是：在同時進行 GCP 遷移的背景下，維護自管 Kafka 的投資回報比不上切換到託管方案。這個判斷跟 Kafka 本身的能力無關 — Kafka 0.8+ 的可靠性已經解決了 0.7 的問題。決策的關鍵變數是「組織正在往哪走」，不只是「技術上哪個更好」。

## 回寫教材的連結

- [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)：cross-region replication 跟 MirrorMaker 的進階主題。Spotify 的案例是「早期版本限制」的歷史教訓，Kafka 3.x 的 KRaft + idempotent producer 已解決這些問題。
- [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/)：託管 MQ 的定位跟適用場景。
- [3.6 processing recovery semantics](/backend/03-message-queue/processing-recovery-semantics/)：exactly-once 語意的工程實踐。Spotify 案例揭露 exactly-once 在早期 Kafka 版本不成立。
- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：broker 版本跟可靠性保證的關係。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 使用舊版 Kafka（< 2.0）且跨 region replication 的資料完整性無法驗證
- Broker restart 後需要人工重啟 producer、運維成本跟 broker 數量成正比
- 組織正在做基礎設施遷移（on-prem → cloud），考慮是否同步切換 MQ
- 評估「升級現有系統 vs 遷移到新系統」的決策框架

## 引用源

- [Spotify's Event Delivery — The Road to the Cloud (Part II)](https://engineering.atspotify.com/2017/03/spotifys-event-delivery-the-road-to-the-cloud-part-ii)
