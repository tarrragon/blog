---
title: "Queue 緩衝"
date: 2026-06-20
description: "在 ingestion 和 processing 之間加 message queue 做 burst 緩衝 — Kafka / NATS / Redis Streams 的選型和引入條件"
weight: 3
tags: ["devops", "burst-traffic", "queue", "kafka", "nats", "redis-streams", "buffering"]
---

Message queue 放在 ingestion（接收事件）和 processing（寫入 storage）之間，把兩者解耦。Ingestion 只負責驗證和寫入 queue，processing 按自己的速度從 queue 消費。Queue 做 burst 的時間緩衝 — 高峰時 queue 積壓、低峰時 worker 追上。

## 為什麼不直接寫 DB

直接寫 DB（SQLite / PostgreSQL）的問題是 ingestion 速度被 DB 寫入速度限制。DB 寫入慢（鎖定、WAL flush、索引更新）時，HTTP handler 的 goroutine 等在 `Storage.Store()` 上 — goroutine 積壓 → 記憶體上升 → 最終 OOM 或 response timeout。

Queue 的解決方式是把「接收」和「寫入」分開：接收端只做 JSON 驗證 + 寫入 queue（微秒級），處理端從 queue 讀取 + 寫入 DB（毫秒級）。接收端的吞吐量不再受 DB 限制。

### 取捨

| 維度     | 直接寫 DB                     | 經過 Queue                               |
| -------- | ----------------------------- | ---------------------------------------- |
| 延遲     | 事件寫完 DB 即可查詢          | 事件要等 worker 消費後才可查詢           |
| 吞吐     | 受 DB 寫入速度限制            | 受 queue 寫入速度限制（通常遠高於 DB）   |
| 複雜度   | 一個元件                      | 三個元件（collector + queue + worker）   |
| 故障模式 | DB 掛了事件丟失（除非有背壓） | Queue 做持久化，DB 掛了事件在 queue 等待 |

自用工具場景不需要 queue — 單 collector + SQLite 的直接寫入足夠。Queue 的引入條件是「直接寫 DB 的背壓開始頻繁觸發」。

## 候選類型

| Queue              | 特點                         | 適用場景                               |
| ------------------ | ---------------------------- | -------------------------------------- |
| **Kafka**          | 高吞吐、持久化、消費者群組   | 大規模（> 10 萬 events/sec）、多消費者 |
| **NATS JetStream** | 輕量、低延遲、Go 原生        | 中型（千 ~ 萬 events/sec）、Go 生態    |
| **Redis Streams**  | 用既有 Redis、XADD/XREAD API | 中型、已有 Redis 基礎設施              |

### 選型判斷

已有 Redis → 先用 Redis Streams（零新增元件）。Go 為主的技術棧 → NATS JetStream（Go 原生 client、單 binary 部署）。需要跨消費者群組或日誌級持久化 → Kafka。

### 引入條件

Queue 的引入是架構複雜度的顯著上升（一個元件變三個）。明確的觸發條件：

- 背壓（429 回應）頻繁觸發（每天 > 100 次）且持續（不只是瞬間 burst）
- 寫入延遲的 P95 超過 500ms（DB 成為瓶頸）
- 需要多個 consumer（同一批事件要送到不同的下游 — analytics DB、alert engine、archive）

## 監控系統的 Queue 架構

```text
SDK ──→ Collector (ingestion only)
           │
           ├─ 驗證 JSON Schema
           ├─ Redaction
           └─ 寫入 Queue
                 │
                 ├── Worker A → PostgreSQL（主 storage）
                 ├── Worker B → 降採樣 → Summary tables
                 └── Worker C → Rule engine → Alert
```

Collector 瘦身為 ingestion-only — 只做接收、驗證、redaction 和寫入 queue。Storage 寫入、降採樣、rule engine 都移到 worker 群。Collector 的吞吐瓶頸從 DB 寫入變成 queue 寫入（queue 的寫入吞吐通常是 DB 的 10-100 倍）。

## 下一步路由

- 突發流量的分類 → [突發流量的分類](/devops/07-burst-traffic/burst-classification/)
- 降級策略 → [降級策略](/devops/07-burst-traffic/degradation-strategy/)
- 規模分級的完整應對 → [規模分級應對表](/devops/07-burst-traffic/scale-tier-response/)
- Queue 的選型和操作實務 → [backend 非同步佇列](/backend/03-message-queue/)
