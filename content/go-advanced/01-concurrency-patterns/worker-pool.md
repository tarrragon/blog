---
title: "1.5 bounded worker pool"
date: 2026-04-22
description: "限制同時執行的 goroutine 數量，讓背景工作有明確容量邊界"
weight: 5
---

bounded worker pool 的核心責任是限制同時執行的工作量。goroutine 很便宜，但工作本身可能佔用 CPU、memory、file descriptor、外部 API quota 或資料庫連線；worker pool 讓容量限制成為程式設計的一部分。

## 預計補充內容

1. 無限制 `go process(job)` 的風險。
2. fixed worker pool 與 job channel 的基本模型。
3. context cancel、queue close 與 worker shutdown。
4. job error 如何回報、聚合或記錄。
5. worker pool 測試如何避免 sleep。

## 與 Backend 教材的分工

本章只處理單一 Go process 內的工作量限制。跨 process 的 consumer group、broker partition、dead-letter queue 與重試政策會放在 [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)。
