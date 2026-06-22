---
title: "3.C50 Capital One：Visibility timeout 設計與 Lambda event source"
date: 2026-05-18
description: "Capital One tech blog 講 SQS + Lambda：visibility timeout 應略高於最大處理時間、Lambda 初 5 個 long polling、可擴 60/min。"
weight: 50
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

Capital One 的 SQS + Lambda 實務揭露了 visibility timeout 的雙邊風險 — 太短導致重複處理、太長延遲 retry — 以及 Lambda event source mapping 的 scaling 行為跟直覺不同的地方。

## 業務背景

Capital One 是美國大型金融機構，tech blog 公開分享了 SQS + Lambda 的 event-driven 架構實踐。金融場景的 message 處理對正確性要求極高 — 重複處理一筆交易跟遺失一筆交易的代價都是具體的金錢損失。

SQS 是 AWS 原生的 managed queue，Lambda 是 serverless compute。兩者搭配的 event source mapping 是 AWS 上最常見的 event-driven 入門架構 — 看起來簡單（SQS → Lambda 自動觸發），但 visibility timeout 跟 Lambda scaling 的互動有不少實務細節。

## 技術挑戰

### Visibility timeout 的雙邊風險

SQS 的 visibility timeout 定義了「consumer 取走訊息後，其他 consumer 多久之後才能再看到這筆訊息」。它是 SQS 的核心容錯機制 — consumer 處理失敗（crash、timeout）時，visibility timeout 到期後訊息重新出現在 queue 裡，讓其他 consumer 接手。

**Timeout 太短**：consumer 還在處理中、visibility timeout 已到期、另一個 consumer 取走同一筆訊息開始處理 — 重複處理。金融場景的重複處理可能導致重複扣款或重複退款。

**Timeout 太長**：consumer 處理失敗、需要等很久 visibility timeout 才到期、訊息才重新出現 — retry 延遲。原本幾秒就能被其他 consumer 接手的訊息，要等 15 分鐘才 retry。

Capital One 的實務建議是 visibility timeout 設為「最大預期處理時間 + 少量緩衝」。例如：最大處理時間 30 秒 → visibility timeout 設 45 秒。

### Lambda event source mapping 的 scaling 行為

Lambda 跟 SQS 的整合透過 event source mapping — Lambda 服務自動從 SQS long polling 取訊息、觸發 Lambda function。使用者不需要自己寫 polling 邏輯。

Capital One 揭露的 scaling 行為跟「Lambda 自動擴展」的直覺不同：

- **初始狀態**：Lambda 啟動 5 個 long polling connection（poller）
- **Scale up**：每分鐘最多新增 60 個 poller instance（每個 instance 處理一批 message）
- **上限**：最多 1000 個並行 batch

這意味著突發流量（queue 瞬間湧入大量訊息）的消化速度不是即時的 — Lambda 需要數分鐘才能 scale 到足夠的並行度。在這段 ramp-up 期間，queue depth 會持續增長。

### Batch size 跟 visibility timeout 的互動

Lambda event source mapping 預設 batch size = 10 — 一次取 10 筆訊息、用一個 Lambda invocation 處理。如果 batch 中的某一筆處理特別慢，整個 batch 的處理時間會被拉長。

Visibility timeout 要覆蓋整個 batch 的處理時間（包含最慢的那一筆），否則 batch 還在處理中、早期取走的訊息 visibility timeout 到期、被其他 poller 重新取走 — 導致重複處理。

## 解法與取捨

| 設計參數           | 建議值                          | 取捨                                               |
| ------------------ | ------------------------------- | -------------------------------------------------- |
| Visibility timeout | 最大處理時間 + 緩衝（例 45 秒） | 太短重複、太長延遲 retry                           |
| Batch size         | 依處理時間變異度調整            | Batch 大省 invocation 費用、但延長 visibility 需求 |
| DLQ                | 設定 maxReceiveCount（例 3 次） | 避免 poison message 無限 retry                     |
| Concurrency limit  | 依下游承受能力設定              | 避免 Lambda 爆量壓垮下游 DB                        |

### Idempotency 作為安全網

Visibility timeout 無法完全避免重複處理（網路分區、Lambda timeout 等邊界條件）。Capital One 的做法是在 Lambda function 內實作 [idempotency](/backend/knowledge-cards/idempotency/) — 用 message ID 做去重，確保同一筆訊息被多次處理時結果相同。

Idempotency 把 visibility timeout 的精確度要求降低 — 即使偶爾重複處理，業務結果仍然正確。Visibility timeout 仍然需要合理設定（降低不必要的重複 invocation 成本），但 idempotency 是「即使設錯也不會造成業務錯誤」的安全網。

## 回寫教材的連結

- [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/)：visibility timeout、in-flight limit、Lambda event source 的進階主題
- [3.6 processing recovery semantics](/backend/03-message-queue/processing-recovery-semantics/)：at-least-once 語意下的 consumer 端 idempotency
- [3.2 durable queue](/backend/03-message-queue/durable-queue/)：visibility timeout 是 SQS 的 delivery guarantee 機制
- [3.8 queue consumer retry replay handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)：DLQ + maxReceiveCount 的 retry 升級策略

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- SQS + Lambda 架構中出現訊息重複處理（CloudWatch 的 `ApproximateNumberOfMessagesNotVisible` 跟 `NumberOfMessagesReceived` 比例異常）
- Lambda function 的 timeout 跟 SQS visibility timeout 的關係沒有明確設計
- 突發流量時 queue depth 持續增長、Lambda 的 concurrent execution 沒有立刻跟上
- Batch processing 中的慢訊息拖慢整個 batch、造成 visibility timeout 到期

## 引用源

- [Using AWS Solutions for Event-Driven Serverless Architectures](https://www.capitalone.com/tech/cloud/using-aws-solutions-for-event-driven-serverless-architectures/)
