---
title: "4.0 Go 並發模型總覽"
date: 2026-04-22
description: "先理解 goroutine、OS thread 與 runtime 排程，再看高併發應用怎麼設計"
weight: 0
---

Go 的並發優勢在於 runtime 讓大量 goroutine 的生命週期、排程與阻塞管理更容易使用。處理高併發時，核心判斷是哪些工作可以並發、哪些資源需要限制，以及 runtime 如何把很多 goroutine 放到有限的 OS thread 上執行。

## 本章目標

學完本章後，你將能夠：

1. 分辨 process、thread 與 goroutine 的角色
2. 理解 Go 並發與平行執行不是同一件事
3. 看懂為什麼 I/O 型服務特別適合 Go
4. 判斷什麼時候應該限制並發數
5. 了解 Redis 與 SQL 在高併發下為什麼要加邊界

---

## 【觀察】goroutine 由 Go runtime 管理

goroutine 是 Go runtime 管理的輕量工作單位，OS thread 則是作業系統實際排程的執行緒。你通常不會直接手動管理 goroutine 對應到哪一條 thread；Go runtime 會負責把很多 goroutine 排程到較少的 OS thread 上。

這表示兩件事：

- 啟動 goroutine 的成本比建立 thread 低得多。
- goroutine 很便宜，不代表下游資源也很便宜。

| 名稱      | 責任                                                    |
| --------- | ------------------------------------------------------- |
| process   | 程式執行的整體容器                                      |
| OS thread | 作業系統真正排程的執行單位                              |
| goroutine | Go runtime 管理的並發工作單位                           |
| runtime   | 負責排程、記憶體管理、阻塞處理與 goroutine 生命週期協調 |

## 【判讀】並發和平行是不同層次

並發的核心意義是「很多工作在時間上交疊」，平行的核心意義是「真的同時在多個核心上跑」。Go 可以讓你很容易建立並發工作，但是否能同時跑在多核心上，還要看 runtime 排程、CPU 數量與工作型態。

對服務開發來說，這個差異很重要：

- I/O-bound 工作通常最適合並發化，因為大部分時間都在等網路、磁碟或外部服務。
- CPU-bound 工作不會因為你加很多 goroutine 就自動變快，反而可能因為排程與同步成本變複雜。

## 【策略】高併發的真正重點是限制下游

Go 的 goroutine 很容易開，但 Redis、SQL、HTTP API、檔案描述元與記憶體 [buffer](../../../backend/knowledge-cards/buffer/) 都有容量上限。高併發設計的核心是替外部資源設邊界，讓 goroutine 數量、下游連線與排隊時間都保持可預期。

常見邊界包括：

- [worker pool](../../../backend/knowledge-cards/worker-pool/) 限制同時處理的工作量
- semaphore 或 [rate limit](../../../backend/knowledge-cards/rate-limit/) 限制入口速率
- [timeout](../../../backend/knowledge-cards/timeout/) / [deadline](../../../backend/knowledge-cards/deadline/) 避免單一請求卡太久
- [queue](../../../backend/knowledge-cards/queue/) 或 buffer 對短暫尖峰提供緩衝
- [backpressure](../../../backend/knowledge-cards/backpressure/) 讓上游看到真實壓力

## 【應用】Redis 與 SQL 都是 I/O 邊界

Redis 與 SQL 在 Go 裡通常都被當成 I/O 操作來看待：goroutine 負責並發發出請求，但真正的瓶頸通常在網路延遲、連線數、鎖競爭、索引、熱點 key 或 [transaction](../../../backend/knowledge-cards/transaction/) 範圍。

這也是為什麼後面的資料存取章節會反覆強調：

- client 或 `sql.DB` 要共用，不要每個 request 都 new
- 每個操作都應該帶 `context`
- 讀取可以大量並發，但要有連線池和 timeout
- 寫入可以並發，但要注意衝突、重試與交易邊界
- 當下游開始飽和時，要有明確的拒絕、排隊或降級策略

## 【延伸】runtime 細節不必現在全背

本章先建立 runtime 閱讀模型：goroutine 很輕，thread 有成本，下游資源有上限，並發要設邊界。runtime 的完整內部實作可以留到 profiling 與效能診斷階段再深入。

更進一步的診斷與觀察，會在後面的 runtime profiling 與 goroutine leak 章節再補。

## 本章先處理

這一章先把 Go 的並發模型講清楚；真正落到資料庫與快取時，可以再看：

- [Backend：資料庫與持久化](../../../backend/01-database/)：看 SQL、transaction、[connection pool](../../../backend/knowledge-cards/connection-pool/) 與 schema 邊界如何承接服務壓力。
- [Backend：快取與 Redis](../../../backend/02-cache-redis/)：看 Redis client、[TTL](../../../backend/knowledge-cards/ttl/)、[eviction](../../../backend/knowledge-cards/eviction/)、presence store 與 [hot key](../../../backend/knowledge-cards/hot-key/) 如何承接服務壓力。
- [bounded worker pool](../../../backend/knowledge-cards/worker-pool/)：把並發數收斂成可控容量。

## 小結

Go 的高併發能力來自 runtime 對 goroutine 的管理，而不是手動操作 thread。只要你能把 goroutine、OS thread、I/O 邊界與下游資源限制分開理解，就能看懂後面所有 worker pool、[WebSocket](../../../backend/knowledge-cards/websocket/)、Redis 與 SQL 的設計決策。
