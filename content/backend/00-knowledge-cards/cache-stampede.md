---
title: "Cache Stampede"
date: 2026-04-23
description: "說明快取同時失效時大量 request 如何壓垮正式來源"
weight: 22
---

Cache stampede 的核心概念是「大量 request 在同一時間遇到 cache miss，並同時打向正式來源」。這個現象常出現在熱門 key 過期、服務重啟、快取清空或活動流量尖峰。

## 概念位置

Cache stampede 是快取失效與下游保護的交界。快取原本用來保護資料庫；若熱門資料同時過期，快取反而會把大量請求集中送到資料庫。

## 可觀察訊號與例子

系統需要處理 stampede 的訊號是 cache miss rate 突然升高，同時資料庫查詢數、latency 與 timeout 上升。熱門文章榜每分鐘整點過期，可能讓所有 request 在同一秒重建同一份資料。

## 設計責任

常見策略包括 singleflight、soft TTL、background refresh、jitter、lock 與 fallback stale data。設計時要讓少數 request 負責重建，多數 request 使用既有資料或等待有界時間。
