---
title: "Prefetch"
date: 2026-04-23
description: "說明 consumer 一次取得多少未完成訊息，以及它如何影響吞吐與公平性"
weight: 59
---

Prefetch 的核心概念是「限制 consumer 一次可以持有多少尚未 ack 的訊息」。它讓 broker 控制訊息分派速度，避免單一 consumer 拿走過多工作。

## 概念位置

Prefetch 是 broker backpressure 與 consumer fairness 的工具。Prefetch 太高會讓慢 consumer 囤積訊息；prefetch 太低會降低吞吐，讓 consumer 閒置等待。

## 可觀察訊號與例子

系統需要調整 prefetch 的訊號是 unacked messages 偏高、某些 consumer 忙碌但其他 consumer 閒置，或單筆工作耗時差異很大。影片轉檔工作長短差異大時，較低 prefetch 能讓工作更公平分配。

## 設計責任

Prefetch 要和 handler 耗時、並發數、ack timeout、下游容量與 retry policy 一起調整。觀測上要看 unacked messages、consumer utilization、處理耗時與 redelivery。
