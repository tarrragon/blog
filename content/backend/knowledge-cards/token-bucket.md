---
title: "Token Bucket"
date: 2026-04-23
description: "說明 token bucket 如何用配額與補充速率控制流量"
weight: 54
---

Token bucket 的核心概念是「用可累積的 token 表示可使用配額」。每次操作消耗 token，系統按固定速率補充 token；bucket 容量決定可容忍的短暫 burst。 可先對照 [Token Revocation](/backend/knowledge-cards/token-revocation/)。

## 跟其他概念的關係

Token bucket 常用於 rate limit、retry budget、API quota、worker admission 與下游保護。它同時表達平均速率與短暫尖峰容忍度。 可先對照 [Token Revocation](/backend/knowledge-cards/token-revocation/)。

## 可觀察訊號與例子

系統需要 token bucket 的訊號是流量有短暫尖峰，但仍需要限制長期平均使用量。第三方 API 每秒可處理固定請求量時，worker 可以用 token bucket 控制呼叫速度。

## 判斷條件與後果

Token bucket 的補充速率決定長期平均使用量的上限，容量決定一次放行多大的 burst：容量很大時，bucket 閒置一段時間後累積滿了，一次放行的請求可能超過下游承受得了的量。消耗單位沒有定義時，大請求與小請求扣同樣的 token，配額量到的不是實際負載。超限行為（拒絕、排隊或降級）沒有定義時，呼叫方不知道該重試還是放棄；沒有觀測欄位（剩餘 token、被拒次數）時，看不出限制是否正在觸發。多 tenant 系統只有一個全域 bucket 時，一個 tenant 的尖峰用光全部 token，其他 tenant 的請求跟著被拒；每個 tenant 各有 bucket、再加一個全域 bucket 保護下游總量時，tenant 之間的公平與下游的上限兩者都成立。
