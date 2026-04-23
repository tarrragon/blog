---
title: "Bulkhead"
date: 2026-04-23
description: "說明 bulkhead 如何用資源分艙限制故障擴散"
weight: 55
---

Bulkhead 的核心概念是「把服務資源分成彼此隔離的艙室」。某個艙室過載或失效時，其他艙室仍保留處理能力。

## 概念位置

Bulkhead 是 dependency isolation 的具體模式。它常用在 thread pool、connection pool、queue、worker group、tenant capacity 與不同優先級工作。

## 可觀察訊號與例子

系統需要 bulkhead 的訊號是單一功能或 tenant 可以拖垮整體服務。大量報表匯出可以放到獨立 worker pool，避免它佔滿處理登入、查詢與付款的資源。

## 設計責任

Bulkhead 設計要定義分艙邊界、容量、排隊策略、拒絕行為與告警。容量切分太細會降低利用率，切分太粗會失去隔離效果。
