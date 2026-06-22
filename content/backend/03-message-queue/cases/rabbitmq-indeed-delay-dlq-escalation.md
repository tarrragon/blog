---
title: "3.C25 Indeed：Delay queue + DLQ 三層 escalation"
date: 2026-05-18
description: "Indeed 每天 35M+ 職缺、設計 Requeue → Delay queue → DLQ 三層 escalation 避開 head-of-line blocking。"
weight: 25
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 retry 策略要跟 queue 拓樸結合設計，分層延遲 + [DLQ](/backend/knowledge-cards/dead-letter-queue/) 的三層 escalation 能避免 head-of-line blocking。

## 業務背景

Indeed 是全球最大的求職搜尋引擎之一，每天處理 35M+ 筆職缺資料的索引、更新與推送。職缺資料從雇主端進入系統後，需要經過解析、標準化、索引、推送到搜尋引擎等多個處理步驟，每個步驟由 RabbitMQ 串接的 consumer 處理。

這個規模下，任何一個處理步驟的暫時失敗（downstream service timeout、資料格式異常、外部 API rate limit）都會產生需要 retry 的訊息。每天有數十萬筆訊息需要至少一次 retry。

## 技術挑戰：Head-of-line blocking

Indeed 原本的 retry 策略是 consumer 處理失敗時把訊息 requeue（`basic.nack` with `requeue=true`）。RabbitMQ 的 requeue 行為是把訊息放回 queue 的 head — 下一次 consumer 拿到的還是這條失敗的訊息。

當一條訊息因為 downstream timeout 反覆失敗時，它會持續佔住 queue head，阻塞後面所有等待處理的訊息。單一 consumer 的時間被一條失敗訊息反覆消耗，其他正常的訊息延遲累積。在 35M+ 筆/天的吞吐量下，一條 head-of-line blocking 訊息就能讓整個 pipeline 的 processing lag 從秒級升到分鐘級。

這個問題的根源是 retry 策略跟 queue 拓樸耦合在一起 — requeue 把 retry 決策留在同一個 queue 裡，讓失敗訊息跟正常訊息搶同一條通道。

## 解法：三層 escalation

Indeed 設計了一個三層 escalation 模型，把失敗訊息依嚴重程度逐層隔離：

### 第一層：Immediate retry（同 queue）

Consumer 處理失敗時，先在 client 端做短暫 backoff（數百毫秒到數秒），然後 ack 原訊息、重新 publish 到同一個 queue 的 tail（而非 requeue 到 head）。

這層處理的是暫態錯誤 — downstream 偶發的 500、短暫的 network hiccup。多數訊息在第一層就能恢復。重新 publish 到 tail 確保失敗訊息排在正常訊息後面，不阻塞其他訊息。

### 第二層：Delay queue

第一層 retry N 次仍然失敗的訊息，透過 RabbitMQ 的 Dead Letter Exchange（DLX）路由到 delay queue。Delay queue 用 `x-message-ttl` 設定延遲時間（例如 30 秒、1 分鐘、5 分鐘），TTL 到期後訊息透過另一個 DLX 路由回原始 queue 的 tail。

Indeed 用多個不同 TTL 的 delay queue 實作 exponential backoff — 第一次進 delay 等 30 秒、第二次等 1 分鐘、第三次等 5 分鐘。這個做法利用 RabbitMQ 原生的 DLX + TTL 機制，不需要額外的 scheduler 或 cron job。

這層處理的是持續性錯誤 — downstream 在做 deployment、外部 API 在做 maintenance。延遲重試讓 downstream 有時間恢復，同時失敗訊息完全離開主 queue、不影響正常處理。

### 第三層：Dead Letter Queue

Delay queue retry M 次後仍然失敗的訊息進入 [DLQ](/backend/knowledge-cards/dead-letter-queue/)。DLQ 中的訊息不再自動重試，需要人工審視或批次 replay。

DLQ 的價值是把「目前無法處理」的訊息安全保存，不讓它們無限消耗 retry 資源。Indeed 的維運團隊定期檢查 DLQ 中的訊息 — 按 error type 分群、判斷是 bug（需要修 code 再 replay）還是資料問題（需要修正資料再 replay）。

## 取捨

**犧牲的是 delivery order**。訊息從 delay queue 回到主 queue tail 時，已經不在原始的位置。對 Indeed 的職缺處理來說，order 不影響正確性 — 職缺更新是 idempotent 的，最終狀態正確即可。對 order-sensitive 的場景，這個模型需要額外的 ordering 機制。

**增加的是拓樸複雜度**。三層 escalation 涉及主 queue + 多個 delay queue + DLQ + 多個 DLX 的 binding。RabbitMQ 的 exchange / queue / binding 組合需要明確規劃跟文件化，否則維運時搞不清楚訊息的路由路徑。

## 回寫教材的連結

- [3.2 durable queue](/backend/03-message-queue/durable-queue/)：DLX + TTL 是 RabbitMQ 原生的 durable 機制
- [3.6 processing recovery semantics](/backend/03-message-queue/processing-recovery-semantics/)：retry 策略跟 consumer 的 ack/nack 行為
- [RabbitMQ DLQ retry escalation](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)：DLX 配置的實作細節
- [3.C6 Uber Kafka 平台](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)：Kafka 生態的 retry topic 跟 DLQ 設計比較

## 判讀徵兆

以下訊號出現時，應該回讀本案例：

- Consumer 的 processing lag 在特定時段突然升高、但訊息產生速率沒變
- 同一條訊息的 retry 佔據 consumer 的大部分處理時間
- Requeue 後訊息立刻又被同一個 consumer 取到、進入 retry 迴圈
- DLQ 中的訊息堆積、沒有定期審視跟 replay 的機制
- Retry 策略只有 client 端 backoff、沒有 queue 拓樸層面的隔離

## 引用源

- [Delaying Messages with RabbitMQ at Indeed](https://engineering.indeedblog.com/blog/2017/06/delaying-messages/)
- [Get a Job 35 Million Times a Day Using RabbitMQ (talk)](https://engineering.indeedblog.com/talks/get-job-35-million-times-day-using-rabbitmq/)
