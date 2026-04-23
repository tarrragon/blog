---
title: "Local Worker"
date: 2026-04-23
description: "說明同一個 process 內的背景工作模型與其生命週期邊界"
weight: 148
---

Local worker 的核心概念是「背景工作仍留在同一個 application process」。它可降低 request 等待時間，但不提供跨 process 的持久可靠保證。

## 概念位置

Local worker 常搭配 [in-process channel](../in-process-channel/) 與 [worker pool](../worker-pool/)；若需求轉向跨節點可靠處理，通常要改用 [durable queue](../durable-queue/)。

## 可觀察訊號與例子

例如非關鍵通知、短週期快取刷新、定時清理記憶體資料，可先由 local worker 承擔。

## 設計責任

設計時要定義停止行為、錯誤處理、隊列上限與 shutdown 合約，避免背景任務在重啟時遺失而不可見。
