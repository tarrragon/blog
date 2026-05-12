---
title: "Saturation Point"
date: 2026-05-12
description: "說明系統從線性穩態進入 latency 指數成長區的關鍵流量點"
weight: 222
---

Saturation point 的核心概念是「系統 latency 從線性穩態進入指數成長的流量臨界點」。容量曲線分三段：linear → knee → cliff。knee point 是設計容量上限（safe operating zone 的邊界）、cliff 是系統極限（已不可用）。可先對照 [Load Test](/backend/knowledge-cards/load-test/)。

## 概念位置

Saturation 不是「系統掛掉」、是「進入 latency 不可預測區」。健康系統運轉在 knee point 以下 50-70%。M/M/c queueing theory 顯示：utilization 接近 80% 時、queue length 跟 latency 指數成長 — 這個 80% 就是常見的 knee。可先對照 [Little's Law](/backend/knowledge-cards/little-law/)。

## 可觀察訊號與例子

Saturation point 出現的訊號是「pressure 增加 10%、latency 增加 100%」。對應案例：[Tixcraft DynamoDB IOPS 從 20 衝到 135K](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — partition 設計均勻時 saturation point 推到極遠；hot partition 場景下 saturation point 提前出現、即使整體 capacity 還有餘。

## 設計責任

容量規劃必須先量出 saturation point、再以 headroom 規劃實際 capacity。沒有量過 saturation point 的系統等於「不知道距離崩潰多遠」。每次重大改動後 re-test、確認 knee 沒往不好的方向移。
