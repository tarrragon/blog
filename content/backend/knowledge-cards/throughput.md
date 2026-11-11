---
title: "Throughput"
tags: ["吞吐量", "Throughput"]
date: 2026-04-23
description: "整理系統單位時間內可處理的工作量"
weight: 1
---

Throughput 的核心概念是「系統在一段時間內完成多少工作」。它和 latency 不同，throughput 看總量與持續處理能力，latency 看單次完成時間。 可先對照 [Thundering Herd](/backend/knowledge-cards/thundering-herd/)。

## 跟其他概念的關係

Throughput 位在容量、排程與流量控制的交界。queue、broker、stream、load test 與 partitioning 都會直接影響 throughput。 可先對照 [Thundering Herd](/backend/knowledge-cards/thundering-herd/)。

## 可觀察訊號

系統需要 throughput 指標的訊號包括：queue lag 上升、consumer 跟不上 producer、load test 失敗、CPU 或 I/O 長期飽和。

## 接近真實網路服務的例子

checkout 每分鐘要處理多少訂單、consumer group 每秒可消化多少事件、load balancer 後面每個 instance 的穩定處理量，都是 throughput 問題。

## 判斷條件與後果

Throughput 的數字帶著測量單位才能比較：每分鐘訂單數與每秒事件數量的是不同的工作，單位不同的兩個數字放在一起得不出結論。整體容量等於單節點穩定處理量乘以節點數，只在瓶頸隨節點一起擴充時成立；瓶頸在共用的資料庫或 broker 時，加節點不增加整體 throughput。流量超過容量時的處理方式也取決於瓶頸位置：瓶頸可以水平擴充時用 scale out，瓶頸是下游的固定上限時用 rate limit 擋在入口，或用 backpressure 讓上游放慢；三者都沒有時，超出的工作在 queue 裡累積，表現為 queue lag 持續上升。
