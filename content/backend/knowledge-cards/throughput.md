---
title: "Throughput"
tags: ["吞吐量", "Throughput"]
date: 2026-04-23
description: "整理系統單位時間內可處理的工作量"
weight: 0
---


Throughput 的核心概念是「系統在一段時間內完成多少工作」。它和 latency 不同，throughput 看總量與持續處理能力，latency 看單次完成時間。 可先對照 [Thundering Herd](/backend/knowledge-cards/thundering-herd/)。

## 概念位置

Throughput 位在容量、排程與流量控制的交界。queue、broker、stream、load test 與 partitioning 都會直接影響 throughput。 可先對照 [Thundering Herd](/backend/knowledge-cards/thundering-herd/)。

## 可觀察訊號

系統需要 throughput 指標的訊號包括：queue lag 上升、consumer 跟不上 producer、load test 失敗、CPU 或 I/O 長期飽和。

## 接近真實網路服務的例子

checkout 每分鐘要處理多少訂單、consumer group 每秒可消化多少事件、load balancer 後面每個 instance 的穩定處理量，都是 throughput 問題。

## 設計責任

Throughput 設計要定義測量單位、瓶頸位置、單節點與整體容量、以及在哪些條件下需要 backpressure、rate limit 或 scale out。
