---
title: "1.5 bounded worker pool"
date: 2026-04-22
description: "限制同時執行的 goroutine 數量，讓背景工作有明確容量邊界"
weight: 5
---

bounded [worker pool](../../backend/knowledge-cards/worker-pool) 的核心責任是限制同時執行的工作量。goroutine 很便宜，但工作本身可能佔用 CPU、memory、file descriptor、外部 API quota 或資料庫連線；worker pool 讓容量限制成為程式設計的一部分。

## 預計補充內容

這些工作量邊界會在下列章節展開：

- [Go 入門：goroutine：背景工作與服務生命週期](../../go/04-concurrency/goroutine/)：先理解 goroutine 的啟動和結束方式，才知道 worker pool 為什麼要限制並發數。
- [Go 入門：channel：事件流與 backpressure ](../../go/04-concurrency/channel/)：job channel 的容量和阻塞行為，會直接影響 pool 的整體策略。
- [Go 進階：select loop 的生命週期設計](select-loop/)：worker 的停止、排空與關閉，通常都要回到 select loop 來說明。
- [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)：真正跨 process 的 [consumer](../../backend/knowledge-cards/consumer)、retry 與 dead-letter 行為屬於這裡。

## 本章不處理

本章先把單一 process 內的工作量上限、停止與排空講清楚；跨 process 的 consumer 與 retry 機制，會放在 [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)。

## 與 Backend 教材的分工

本章只處理單一 Go process 內的工作量限制。跨 process 的 [consumer group](../../backend/knowledge-cards/consumer-group)、[broker](../../backend/knowledge-cards/broker) [partition](../../backend/knowledge-cards/partition)、[dead-letter [queue](../../backend/knowledge-cards/queue)](../../backend/knowledge-cards/dead-letter-queue) 與重試政策會放在 [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)。

## 和 Go 教材的關係

這一章承接的是 goroutine、channel 與 select loop；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](../../go/04-concurrency/goroutine/)
- [Go：channel：資料傳遞與 backpressure ](../../go/04-concurrency/channel/)
- [Go：select：同時等待多種事件](select-loop/)
- [Go：如何新增背景工作流程](../../go/06-practical/new-background-worker/)
