---
title: "3.C43 Arcjet：Redis Streams 取代 Kafka 省 6 位數 $"
date: 2026-05-18
description: "Arcjet security 平台、Kafka managed 6 位數 $/yr、用 Redis Streams 約 $1k/yr、自寫 Janitor 監控 retention。"
weight: 43
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

Arcjet 用 Redis Streams 取代 Kafka 的案例揭露了中小規模場景下「Kafka 的 managed 成本 vs Redis Streams 的運維成本」的具體取捨 — 省下六位數年費的代價是自寫 retention 治理跟監控工具。

## 業務背景

Arcjet 是 security / bot detection 平台，處理每個 HTTP request 的安全判斷。核心需求是 low-latency 的請求處理 — 安全判斷要在幾毫秒內完成，不能拖慢使用者的 request。

系統架構中有一段 event-driven pipeline 負責把安全事件從 detection layer 傳遞到 analytics 跟 alerting。原本評估用 Kafka 做這段 pipeline，但 managed Kafka 的年費落在六位數美金 — 對 Arcjet 的流量規模跟業務階段，這個成本不合理。

Arcjet 的基礎設施已經有 Redis 做 cache。把 Redis 從純 cache 升級到 cache + Streams，利用既有的 Redis infrastructure 承擔 event pipeline，總成本約 $1k/year。

## 技術挑戰

### Redis Streams 沒有自動 retention

Kafka 的 retention 是內建功能 — 設定 `log.retention.hours` 後 broker 自動刪除到期資料。Redis Streams 沒有內建的自動 retention — stream 資料會持續累積，直到手動 `XTRIM` 或 `XDEL`。

在生產環境下，不處理 retention 意味著 Redis 的記憶體持續成長，最終觸發 eviction policy 或 OOM。對 Arcjet 來說 Redis 同時做 cache 跟 Streams，Streams 的記憶體成長會擠壓 cache 的可用空間。

### Consumer group 進度追蹤

Redis Streams 的 consumer group 會追蹤每個 consumer 的讀取進度（last delivered ID）。做 `XTRIM` 時需要確保不刪除尚未被所有 consumer group 確認的訊息 — 否則 consumer 會丟失未處理的事件。

Kafka 的 log compaction 跟 retention 自動處理這個問題（consumer offset 以前的 segment 才會被清理）。Redis Streams 需要 application 自己確認所有 consumer group 的進度，再決定 trim 的位置。

### 單機 Redis 的可靠性邊界

Redis 的持久化機制（RDB snapshot + AOF）提供的是 best-effort 的持久性，跟 Kafka 的 replication-based 持久化保證不同。Redis crash + restart 時，AOF 的最後幾筆寫入可能遺失（取決於 `appendfsync` 設定）。

對 Arcjet 的安全事件場景，偶爾丟失幾筆事件可以接受（security detection 的結果是即時判斷，事後的 analytics 容忍小量遺失）。如果場景是金融交易或 audit log，這個可靠性邊界就不夠。

## 解法與取捨

### 自建 Janitor process

Arcjet 自寫了一個 Janitor process 處理 Redis Streams 的 retention：

1. 定期檢查每個 stream 的長度（`XLEN`）
2. 查詢所有 consumer group 的 pending entry list（PEL）跟最後確認位置
3. 計算安全的 trim 位置（所有 consumer group 都已確認的最舊 ID）
4. 執行 `XTRIM stream MINID <safe-id>` 刪除已確認的舊資料

Janitor 的執行頻率根據實際處理速度（~100 msgs/min）設定 — 不需要非常頻繁，但不能完全不跑。

### 取捨

| 面向           | Managed Kafka                  | Redis Streams + Janitor         |
| -------------- | ------------------------------ | ------------------------------- |
| 年成本         | 六位數 USD                     | ~$1k USD                        |
| Retention 管理 | 內建自動                       | 自寫 Janitor                    |
| 持久化保證     | Replication-based（強）        | AOF/RDB（best-effort）          |
| Consumer group | 原生支援、offset commit 自動   | 原生支援、但 trim 要手動協調    |
| 生態工具       | Kafka Connect、Schema Registry | 無（自建）                      |
| 擴展性         | Partition 水平擴展             | 單 Redis 受限、Cluster 模式複雜 |
| 運維知識       | Kafka 運維（或交給 managed）   | Redis 運維 + 自建 Janitor 維護  |

### 適用邊界

Redis Streams 取代 Kafka 的適用邊界：

- **流量規模**：每分鐘數百到數千筆（超過每秒數萬筆需要 Redis Cluster 或多 stream）
- **持久化要求**：容忍偶爾丟失少量訊息（best-effort）
- **已有 Redis**：不需要額外部署 Redis、利用既有 infrastructure
- **Kafka 功能不需要**：不需要 Kafka Connect、Schema Registry、long-term retention、跨 region replication

超過這些邊界時，Redis Streams 的自建成本（Janitor + 監控 + retention 治理 + 可靠性補償）會逐漸接近 managed Kafka 的費用，成本優勢消失。

## 回寫教材的連結

- [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/)：XCLAIM / PEL recovery 的進階主題
- [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)：成本對照 — Kafka 的固定成本高但功能完整
- [3.2 durable queue](/backend/03-message-queue/durable-queue/)：Redis Streams 的持久化機制跟 Kafka 的 replication 在 durability 光譜上的位置
- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：broker 選型時成本是一級決策維度

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- Managed Kafka 的月帳單跟實際流量量級不成比例（低流量但高成本）
- 已有 Redis infrastructure、考慮把 event pipeline 合併到 Redis
- Event pipeline 的流量在每秒數百筆以下、持久化要求是 best-effort
- Redis 記憶體持續成長但不確定 Streams 的 retention 有沒有正確執行

## 引用源

- [Replacing Kafka with Redis Streams](https://blog.arcjet.com/replacing-kafka-with-redis-streams/)
