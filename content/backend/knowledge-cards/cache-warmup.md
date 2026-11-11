---
title: "Cache Warmup"
date: 2026-04-23
description: "說明服務啟動或活動前如何預先建立快取資料"
weight: 91
---

Cache warmup 的核心概念是「在正式流量大量進入前預先載入快取」。它降低 cold start 與 cache miss 對下游造成的尖峰壓力。 可先對照 [Cascading Failure](/backend/knowledge-cards/cascading-failure/)。

## 跟其他概念的關係

Warmup 是快取與部署流程的交界。新 instance、Redis 清空、熱門活動開始或版本切換時，快取可能是空的；warmup 可以先建立高價值資料。 可先對照 [Cascading Failure](/backend/knowledge-cards/cascading-failure/)。

## 可觀察訊號與例子

系統需要 warmup 的訊號是部署後前幾分鐘 latency 升高，或活動開始時資料庫突然被打滿。大型促銷前，可以預先載入熱門商品、價格與庫存摘要。

## 判斷條件與後果

Warmup 本身是一批對下游的讀取，和正式流量打在同一個資料來源上。沒有速率限制時，warmup 在部署當下自己造成它要防的那一波尖峰；warmup 的流量沒有算進容量規劃時，一次上線多台新 instance，下游同時承受多份 warmup。載入順序決定有限時間內先暖到哪些資料：先載入高價值資料（熱門商品、價格與庫存摘要）時，warmup 還沒完成就接流量，也能命中大部分請求。warmup 和 readiness 的關係決定 instance 何時接流量：readiness 不等 warmup 時，instance 以空快取接流量，等於沒有 warmup；readiness 等 warmup、而 warmup 失敗時的行為沒有定義時，instance 一直不進入 ready，部署停在那一批。
