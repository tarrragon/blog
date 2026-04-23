---
title: "Backend 服務實務指南"
date: 2026-04-22
description: "整理資料庫、快取、訊息佇列、觀測、部署與可靠性驗證等後端服務能力"
weight: 34
---

Backend 教材的核心目標是整理「應該被 application interface 隔離」的外部服務能力。語言教材負責各自的語法、標準庫、並發或非同步模型、測試方法與 interface / protocol 邊界；Backend 教材負責資料庫、快取、訊息佇列、觀測平台、部署平台與系統可靠性。

這個切分讓不同語言的學習保持清楚：Go、Python 或其他後端語言可以各自說明如何定義抽象邊界、處理取消與逾時、回傳錯誤、寫 fake 或 contract test；Backend 章節則說明 SQLite、PostgreSQL、Redis、RabbitMQ、broker、migration、metrics、tracing、Kubernetes 等具體技術如何運作。

Backend 不是 Go 教材的附屬章節，而是多個後端語言系列共用的實作層。未來若新增 frontend、data engineering、machine learning、mobile 或其他非後端主題，也可以用同樣方式把共用實作知識抽成獨立資料夾，而不是塞進特定語言底下。

## 教材邊界

| 類型       | 放在語言教材                                                                                | 放在 Backend 教材                                                                 |
| ---------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 資料存取   | repository port、interface / protocol、context / cancellation、error、contract test         | SQLite、PostgreSQL、transaction、schema migration、index、isolation level         |
| 快取       | cache port、TTL 概念、資料複製邊界、失效策略的程式邊界                                      | Redis 資料型別、eviction、distributed lock、cache aside、pub/sub                  |
| 訊息傳遞   | channel / queue abstraction、backpressure、publisher port、processor、idempotency interface | RabbitMQ、NATS、Kafka、Redis Streams、ack/nack、dead-letter queue、consumer group |
| 可觀測性   | 標準 logger、runtime 訊號、diagnostics endpoint、trace context 邊界                         | log aggregation、Prometheus、OpenTelemetry、trace、dashboard、alert               |
| 部署平台   | graceful shutdown、health/readiness、signal handling、resource limit 的程式設計             | Kubernetes、systemd、load balancer、container image、service discovery            |
| 可靠性驗證 | unit test、table-driven / parameterized test、race / async test、integration test           | CI pipeline、load test、fuzz campaign、chaos testing、環境治理                    |

## 教學模組

### [模組一：資料庫與持久化](01-database/)

整理 relational database、embedded database、transaction、migration、repository adapter 與資料一致性。

### [模組二：快取與 Redis](02-cache-redis/)

整理 cache aside、TTL、eviction、Redis data structure、distributed lock、pub/sub 與快取一致性。

### [模組三：訊息佇列與事件傳遞](03-message-queue/)

整理 durable queue、broker、ack/nack、retry、dead-letter queue、outbox、idempotency 與 consumer 設計。

### [模組四：可觀測性平台](04-observability/)

整理 structured log aggregation、metrics、tracing、dashboard、alert 與操作診斷流程。

### [模組五：部署平台與網路入口](05-deployment-platform/)

整理 Kubernetes、systemd、load balancer、container、service discovery、rolling update 與平台合約。

### [模組六：可靠性驗證流程](06-reliability/)

整理 CI、load test、fuzz、chaos testing、測試環境與回歸驗證策略。

## 與語言教材的關係

Backend 教材承接語言教材中的外部技術邊界。語言章節會先建立「如何隔離」的能力；Backend 章節再說明「被隔離的技術本身」。

以 Go 為例，建議閱讀路線：

1. 先讀 [Go：用 interface 隔離外部依賴](../go/07-refactoring/interface-boundary/)
2. 再讀 [Go：如何新增 repository port](../go/06-practical/repository-port/)
3. 接著依需求進入 database、cache、queue、observability 或 deployment 分類

Python 教材後續也可以用同樣方式對齊：Python 章節說明 protocol、abstract base class、async context、dependency injection、pytest fixture 與測試替身；Backend 章節說明資料庫、Redis、message broker、觀測與部署平台的實作語意。

## 與 Go 案例的關係

前面的 Go 案例模組已經把高併發、長連線、事件處理、資料庫與雲端基礎設施場景說明得很清楚。Backend 教材接下來要做的事情，就是把這些服務型態拆成具體技術主題：

- [Cloudflare 與長連線服務](../go/08-case-studies/cloudflare/)
- [Cockroach Labs 與分散式 SQL](../go/08-case-studies/cockroach-labs/)
- [Stream 與即時 feed / chat](../go/08-case-studies/stream/)
- [ByteDance / CloudWeGo 與微服務治理](../go/08-case-studies/cloudwego/)

這些案例提供了「為什麼需要這些後端實作主題」的來源，而 Backend 模組則提供「這些主題本身怎麼運作」的說明。

## 暫定章節來源

目前 Backend 目錄先承接 Go 與 Python 後端教材都會遇到的外部實作議題：

- 資料庫 transaction、schema migration、isolation level
- durable queue、outbox、idempotency store
- Redis、distributed cache、presence store
- metrics、tracing、log aggregation、OpenTelemetry
- Kubernetes、systemd、load balancer、container runtime
- CI、load test、fuzz、chaos testing

後續撰寫任何語言教材時，凡是涉及具體外部服務操作、部署平台設定或產品選型，都應優先放到 Backend；語言章節只保留足夠說明抽象邊界的最小背景。

---

_文件版本：v0.1.0_
_最後更新：2026-04-22_
_系列狀態：分類索引建立中_
