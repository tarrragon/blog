---
title: "Jitter"
date: 2026-04-23
description: "說明重試或排程加入隨機偏移如何降低同步尖峰"
weight: 47
---

Jitter 的核心概念是「在重試、排程或過期時間中加入隨機偏移」。它讓大量 client、worker 或 cache key 的動作分散發生，降低同一時間打向下游的尖峰。 可先對照 [Least Privilege](/backend/knowledge-cards/least-privilege/)。

## 跟其他概念的關係

Jitter 是反同步尖峰工具。Exponential backoff 只會拉長間隔；若所有 client 同時開始、使用同一公式，下一波重試仍可能同時抵達。Jitter 讓這些重試分散。 可先對照 [Least Privilege](/backend/knowledge-cards/least-privilege/)。

## 可觀察訊號與例子

系統需要 jitter 的訊號是整點、部署後、cache 過期後或故障恢復後出現同步流量尖峰。大量 worker 在同一秒重試失敗 job，可能讓剛恢復的下游再次被打滿。

## 判斷條件與後果

一個動作的觸發時間由共同的起點加上固定間隔算出時，大量 client 或 worker 的下一次動作會在同一時刻發生。retry delay、TTL、排程 job、polling interval 與 client reconnect 都符合這個條件：它們的起點分別是同一次故障、同一批寫入的 cache、整點、部署完成或連線中斷的那一刻。這些位置沒有加 jitter 時，下游剛恢復就再收到一波同步的尖峰，可能再次被打滿。加了 jitter 之後，效果從三個觀測確認：重試時間的分布是否攤開、尖峰流量是否下降、下游恢復時間是否縮短。
