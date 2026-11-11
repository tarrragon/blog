---
title: "Prefetch"
date: 2026-04-23
description: "說明 consumer 一次取得多少未完成訊息，以及它如何影響吞吐與公平性"
weight: 60
---

Prefetch 的核心概念是「限制 consumer 一次可以持有多少尚未 ack 的訊息」。它讓 broker 控制訊息分派速度，避免單一 consumer 拿走過多工作。 可先對照 [Probe](/backend/knowledge-cards/probe/)。

## 跟其他概念的關係

Prefetch 是 broker backpressure 與 consumer fairness 的工具。Prefetch 太高會讓慢 consumer 囤積訊息；prefetch 太低會降低吞吐，讓 consumer 閒置等待。 可先對照 [Probe](/backend/knowledge-cards/probe/)。

## 可觀察訊號與例子

系統需要調整 prefetch 的訊號是 unacked messages 偏高、某些 consumer 忙碌但其他 consumer 閒置，或單筆工作耗時差異很大。影片轉檔工作長短差異大時，較低 prefetch 能讓工作更公平分配。

## 判斷條件與後果

Prefetch 的合適值由 handler 耗時、並發數、ack timeout、下游容量與 retry policy 一起決定，只調 prefetch 一項時，後果出現在其他幾項上。一個 consumer 持有的訊息在 ack timeout 內處理不完時（prefetch 高、單筆耗時長），排在後面的訊息還沒開始處理就逾時，被 broker 重新投遞，redelivery 增加，同一則訊息可能被處理兩次；prefetch 調高而下游容量不變時，consumer 拿到更多訊息，壓力轉到下游；單筆耗時差異大時（影片轉檔），高 prefetch 讓慢 consumer 囤積訊息而其他 consumer 閒置。Unacked messages、consumer utilization、處理耗時與 redelivery 放在一起看：unacked 高而 utilization 不均，代表訊息分派不公平；redelivery 上升，代表持有的訊息超過 ack timeout 內處理得完的量。
