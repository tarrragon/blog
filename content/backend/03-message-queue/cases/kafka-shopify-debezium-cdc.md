---
title: "3.C13 Shopify：Debezium CDC over sharded MySQL"
date: 2026-05-18
description: "Shopify 100+ MySQL shard、150 Debezium connector、Black Friday 100K records/sec P99 < 10s。"
weight: 13
tags: ["backend", "message-queue", "case-study", "kafka"]
---

Shopify 的 CDC pipeline 揭露了 sharded monolith 上大規模 log-based CDC 的真實工程壓力。壓力集中在 snapshot 跟 oversized payload，穩態複製本身反而是最穩定的部分。

## 業務背景

Shopify 的核心資料儲存是 100+ 個 MySQL shard，每個 shard 承載不同商家的交易資料。下游系統（搜尋索引、analytics、資料倉儲）需要近即時地取得資料變更。原本用 query-based 方案（內部系統 Longboat）輪詢資料庫，但隨 shard 數量跟資料量成長，輪詢的延遲跟資料庫負載壓力持續惡化。

遷移到 log-based CDC（Debezium over Kafka Connect）後，pipeline 的穩態規模是 ~150 個 Debezium connector 跑在 12 個 Kubernetes pod、Black Friday peak 100K records/sec、P99 latency < 10s。

## 技術挑戰

### Snapshot 鎖定 read replica

Debezium 在初始同步（snapshot）時需要取得一致性快照。MySQL connector 的預設行為是對 read replica 取 global read lock，鎖住的時間跟表大小成正比。Shopify 的大表 snapshot 可能鎖住 read replica 數小時，影響線上查詢。

Shopify 工程師直接向 Debezium 上游貢獻了「lock-free snapshot」機制 — 用 MySQL 的 GTID（Global Transaction ID）確保一致性，取代 global read lock。這個改動後來合併進 Debezium 主線，所有使用者都受益。

### Oversized record

MySQL 的 blob / text 欄位可能產生超過 1 MB 的 CDC record。Kafka 的 message size limit（預設 1 MB）會讓這些 record 被 producer 拒絕。調大 `max.message.bytes` 是一個選項，但會影響 broker 的記憶體跟 replication 效率。

Shopify 的解法是把 oversized payload 寫到 GCS（Google Cloud Storage），CDC record 只帶 GCS pointer。Consumer 端在需要完整資料時再從 GCS 取。這個 pattern 把 Kafka 維持在「傳遞事件 metadata」的定位，大型 payload 走 object storage。

### Connector 故障隔離

150 個 connector 跑在 12 個 pod 上，一個 connector 的 failure（例如某個 shard 的 MySQL 做了 schema change、binlog 格式不相容）可能影響同 pod 上的其他 connector。Shopify 用 Kafka Connect 的 distributed mode + task rebalance 做故障隔離，但 rebalance 本身在 connector 數量多時有延遲。

## 解法與取捨

| 挑戰             | 解法                         | 取捨                                                    |
| ---------------- | ---------------------------- | ------------------------------------------------------- |
| Snapshot 鎖定    | Lock-free snapshot（GTID）   | 需要 MySQL 啟用 GTID、upstream contribution 維護成本    |
| Oversized record | GCS pointer 替代 inline data | Consumer 端要多一步 GCS 讀取、增加端到端延遲            |
| Connector 隔離   | Distributed mode + rebalance | Rebalance storm 在大量 connector 時可能造成全域暫停     |
| 高峰流量         | 12 pod K8s 部署、水平擴展    | Pod 數量增加讓 Kafka Connect worker 的 rebalance 更複雜 |

## 回寫教材的連結

- [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)：CDC 是 outbox pattern 的 log-based 替代方案。Shopify 的 case 揭露 CDC 的工程成本集中在 snapshot 跟 schema evolution，outbox 的成本集中在應用層 dual-write。
- [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)：Kafka Connect / CDC 的進階主題。
- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：message size limit 跟 broker 資源的關係。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- CDC snapshot 過程持續數小時、鎖住 read replica 影響線上查詢
- CDC record size 頻繁超過 Kafka 的 message size limit
- Kafka Connect connector 數量超過 50 個、rebalance 時間開始明顯增長
- 從 query-based 同步（輪詢）切換到 log-based CDC 的評估階段

## 引用源

- [Capturing Every Change From Shopify's Sharded Monolith](https://shopify.engineering/capturing-every-change-shopify-sharded-monolith)
