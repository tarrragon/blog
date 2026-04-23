---
title: "Token Bucket"
date: 2026-04-23
description: "說明 token bucket 如何用配額與補充速率控制流量"
weight: 53
---

Token bucket 的核心概念是「用可累積的 token 表示可使用配額」。每次操作消耗 token，系統按固定速率補充 token；bucket 容量決定可容忍的短暫 burst。

## 概念位置

Token bucket 常用於 rate limit、retry budget、API quota、worker admission 與下游保護。它同時表達平均速率與短暫尖峰容忍度。

## 可觀察訊號與例子

系統需要 token bucket 的訊號是流量有短暫尖峰，但仍需要限制長期平均使用量。第三方 API 每秒可處理固定請求量時，worker 可以用 token bucket 控制呼叫速度。

## 設計責任

Token bucket 要定義補充速率、容量、消耗單位、超限行為與觀測欄位。多 tenant 系統還要區分全域 bucket 與 tenant bucket，保護公平性。
