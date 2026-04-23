---
title: "Cache Warmup"
date: 2026-04-23
description: "說明服務啟動或活動前如何預先建立快取資料"
weight: 90
---

Cache warmup 的核心概念是「在正式流量大量進入前預先載入快取」。它降低 cold start 與 cache miss 對下游造成的尖峰壓力。

## 概念位置

Warmup 是快取與部署流程的交界。新 instance、Redis 清空、熱門活動開始或版本切換時，快取可能是空的；warmup 可以先建立高價值資料。

## 可觀察訊號與例子

系統需要 warmup 的訊號是部署後前幾分鐘 latency 升高，或活動開始時資料庫突然被打滿。大型促銷前，可以預先載入熱門商品、價格與庫存摘要。

## 設計責任

Warmup 要定義資料來源、載入順序、速率限制、失敗行為與 readiness 關係。Warmup 本身也會產生下游流量，因此要納入容量規劃。
