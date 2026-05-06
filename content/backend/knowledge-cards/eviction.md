---
title: "Eviction"
date: 2026-04-23
description: "說明快取容量不足時哪些資料會被淘汰，以及淘汰如何影響服務"
weight: 19
---


Eviction 的核心概念是「容量不足時系統選擇移除哪些資料」。快取與記憶體型服務需要 eviction policy，因為可用容量有限，資料量與 hot key 會隨流量變化。 可先對照 [Excessive Data Exposure](/backend/knowledge-cards/excessive-data-exposure/)。

## 概念位置

Eviction 處理的是容量控制，TTL 處理的是時間有效性。Redis、CDN、local cache 都可能在容量壓力下淘汰資料；被淘汰的資料若可重建，系統會承擔額外查詢成本。 可先對照 [Excessive Data Exposure](/backend/knowledge-cards/excessive-data-exposure/)。

## 可觀察訊號與例子

系統需要關注 eviction 的訊號是 cache hit rate 突然下降、Redis memory 接近上限、下游資料庫壓力升高。熱門商品活動可能讓大量 key 進入快取，造成原本常用資料被擠出。

## 設計責任

Eviction 策略要搭配 key 設計、容量規劃、資料重要性與告警。高價值或難重建資料應有更穩定的保存方式，一般快取淘汰策略只適合可重建資料。
