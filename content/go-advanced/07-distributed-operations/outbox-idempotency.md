---
title: "7.2 Durable queue、outbox 與 idempotency"
date: 2026-04-22
description: "設計跨 process 事件傳遞的可靠性與去重邊界"
weight: 2
---

# 7.2 Durable queue、outbox 與 idempotency

跨 process 事件傳遞的核心責任是讓事件在失敗、重試與重複投遞下仍維持可預期語意。Channel 只能處理單一 process 內的背壓；durable queue、outbox 與 idempotency store 才能處理服務重啟、網路失敗與 consumer 重試。

## 前置章節

- [Go 進階：非阻塞送出與事件丟棄策略](../01-concurrency-patterns/non-blocking-send/)
- [Go 進階：事件去重與語義鍵設計](../04-architecture-boundaries/dedup-key/)
- [Go 進階：多來源 event 融合](../04-architecture-boundaries/event-fusion/)

## 後續撰寫方向

1. Outbox 如何避免「狀態已寫入，但事件沒送出」的半成功。
2. Idempotency key 如何和 domain dedup key 分工。
3. Consumer retry、dead-letter queue 與 poison message 如何設計處理流程。
4. At-least-once delivery 下，processor 如何保持可重入。
5. Queue lag、retry count、dead-letter count 應如何進入 log 與 metric。

## 本章不處理

本章不追求 exactly-once 的口號。教材重點會放在 Go 服務如何承認 at-least-once 的現實，並用 idempotent processor、outbox 與可觀測欄位降低風險。
