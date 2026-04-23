---
title: "Cache Hit Rate"
date: 2026-04-23
description: "說明快取命中比例如何衡量加速效果與下游保護"
weight: 89
---

Cache hit rate 的核心概念是「快取命中次數佔總讀取次數的比例」。它用來衡量快取是否真的承擔讀取流量。

## 概念位置

Hit rate 是容量與成本指標。低 hit rate 可能代表快取資料不適合、key 太分散、TTL 太短、資料經常失效或工作負載不重複。

## 可觀察訊號與例子

系統需要 hit rate 的訊號是 Redis 成本上升但資料庫壓力仍高。若搜尋結果每次 query 都不同，快取命中率可能很低；商品詳情這類重複讀取則更適合快取。

## 設計責任

Hit rate 要搭配 latency、下游 query count、cache size 與資料新鮮度一起看。高 hit rate 也要確認資料正確性，因為過期資料命中仍可能造成產品問題。
