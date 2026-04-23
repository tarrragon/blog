---
title: "7.2 Durable queue、outbox 與 idempotency"
date: 2026-04-22
description: "設計跨 process 事件傳遞的可靠性與去重邊界"
weight: 2
---

跨 process 事件傳遞的核心責任是讓事件在失敗、重試與重複投遞下仍維持可預期語意。Channel 只能處理單一 process 內的背壓；durable queue、[outbox](../../backend/00-knowledge-cards/outbox-pattern/) 與 [idempotency](../../backend/00-knowledge-cards/idempotency/) store 才能處理服務重啟、網路失敗與 consumer 重試。

## 本章目標

學完本章後，你將能夠：

1. 理解 outbox 為什麼能避免半成功
2. 分辨 domain dedup key 與 idempotency key 的用途
3. 設計可重入的 consumer / processor
4. 用 retry、DLQ 與回補流程處理失敗事件
5. 把事件可靠性寫進資料結構，讓規則可以被程式與測試驗證

## 前置章節

- [Go 進階：非阻塞送出與事件丟棄策略](../01-concurrency-patterns/non-blocking-send/)
- [Go 進階：事件去重與語義鍵設計](../04-architecture-boundaries/dedup-key/)
- [Go 進階：多來源 event 融合](../04-architecture-boundaries/event-fusion/)
- [Backend：Ack / Nack](../../backend/00-knowledge-cards/ack-nack/)
- [Backend：Retry Policy](../../backend/00-knowledge-cards/retry-policy/)
- [Backend：Dead-Letter Queue](../../backend/00-knowledge-cards/dead-letter-queue/)
- [Backend：Consumer Lag](../../backend/00-knowledge-cards/consumer-lag/)

## 後續撰寫方向

1. Outbox 如何避免「狀態已寫入，但事件沒送出」的半成功。
2. Idempotency key 如何和 domain dedup key 分工。
3. Consumer retry、dead-letter queue 與 poison message 如何設計處理流程。
4. At-least-once delivery 下，processor 如何保持可重入。
5. Queue lag、retry count、dead-letter count 應如何進入 log 與 metric。

## 【觀察】outbox 是把資料與事件綁在同一個 transaction

outbox 的核心概念是：先把業務狀態與待發事件一起寫進資料庫，再由獨立 publisher 把 outbox 內容送到 queue 或 broker。這樣即使 process 在寫完資料後當機，也不會丟掉事件。

典型流程是：

1. usecase 開 transaction。
2. 寫入 domain data。
3. 寫入 outbox record。
4. commit。
5. background publisher 讀出未送出的 outbox。
6. 成功後把 outbox 標成已送出。

這個模型的重點是讓「至少會被發現並補送」成為可能。它承認跨 process 傳遞很難保證絕對只送一次，所以後續還要搭配 idempotency。

## 【判讀】idempotency 是跨 process 的必要邊界

只要事件可能重送，consumer 就要能承受重複訊息。idempotent processor 的核心是讓同一筆事件重複進來時，結果仍然穩定。

常見做法包括：

- 用 event ID 記錄已處理過的訊息
- 用 domain key 去重，讓同一個業務操作不會重複套用
- 用狀態機檢查 transition 是否已發生

## 【策略】DLQ 是流程的一部分

當事件重試失敗，dead-letter queue 要變成可處理的操作流程。你要知道：

- 為什麼失敗
- 要重試幾次
- 什麼錯誤可以直接放棄
- 什麼錯誤需要人工回補

如果沒有這些規則，DLQ 只會變成看不完的黑洞。

## 【執行】可重入 processor 的基本形式

可重入的核心要求是同一事件重跑時，不會把資料弄壞。簡化的處理流程通常長這樣：

```go
func (p *Processor) Handle(ctx context.Context, evt Event) error {
    if p.store.Seen(evt.ID) {
        return nil
    }

    if err := p.store.Apply(ctx, evt); err != nil {
        return err
    }

    return p.store.MarkSeen(ctx, evt.ID)
}
```

實際實作時，`Seen` 與 `MarkSeen` 通常要跟業務狀態放在同一個一致性邊界裡，避免競態。

## 【延伸】queue lag 與 retry 需要被觀測

只要有 durable queue，就一定會有 backlog、retry 與 failure pattern。這些訊號應進入 log 與 metric，讓工程師知道是 producer 變慢、consumer 壞掉，還是下游依賴正在抖動。

## 本章不處理

本章不追求 exactly-once 的口號。教材重點會放在 Go 服務如何承認 at-least-once 的現實，並用 idempotent processor、outbox 與可觀測欄位降低風險。

## 和 Go 教材的關係

這一章承接 Go 的事件邊界與非阻塞送出；如果你要先回看語言教材，可以讀：

- [Go 進階：非阻塞送出與事件丟棄策略](../01-concurrency-patterns/non-blocking-send/)
- [Go 進階：事件去重與語義鍵設計](../04-architecture-boundaries/dedup-key/)
- [Go 進階：多來源 event 融合](../04-architecture-boundaries/event-fusion/)
