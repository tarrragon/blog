---
title: "模組三：流量管控"
date: 2026-06-20
description: "收到的流量超過處理能力時怎麼辦 — 背壓、rate limit、熔斷、bulkhead 四種防護機制"
weight: 3
tags: ["devops", "traffic-management", "backpressure", "rate-limit", "circuit-breaker", "bulkhead"]
---

回答「收到的流量超過處理能力時怎麼辦」。四種防護機制各自處理不同層面的過載問題。

## 待寫章節

- [x] 背壓機制（下游慢時上游怎麼減速）
- [x] Rate Limiting（主動限制每個來源的請求速率）
- [x] 熔斷器（依賴服務失敗時怎麼快速失敗而非拖慢自己）
- [x] Bulkhead 隔離（不同工作負載的資源池隔離）

## 跨分類引用

- → [monitoring 模組四 Collector](/monitoring/04-collector/)：Collector 的 ingestion 防護是本模組的應用場景
- → [devops 模組七 突發流量](/devops/07-burst-traffic/)：突發流量時這四種機制怎麼組合使用
- → [backend 可靠性](/backend/06-reliability/)：熔斷和 bulkhead 也是 backend 的可靠性設計元件
