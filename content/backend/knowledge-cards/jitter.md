---
title: "Jitter"
date: 2026-04-23
description: "說明重試或排程加入隨機偏移如何降低同步尖峰"
weight: 46
---

Jitter 的核心概念是「在重試、排程或過期時間中加入隨機偏移」。它讓大量 client、worker 或 cache key 的動作分散發生，降低同一時間打向下游的尖峰。

## 概念位置

Jitter 是反同步尖峰工具。Exponential backoff 只會拉長間隔；若所有 client 同時開始、使用同一公式，下一波重試仍可能同時抵達。Jitter 讓這些重試分散。

## 可觀察訊號與例子

系統需要 jitter 的訊號是整點、部署後、cache 過期後或故障恢復後出現同步流量尖峰。大量 worker 在同一秒重試失敗 job，可能讓剛恢復的下游再次被打滿。

## 設計責任

Jitter 要用在 retry delay、TTL、排程 job、polling interval 與 client reconnect。觀測上要看重試分布、尖峰流量與下游恢復時間。
