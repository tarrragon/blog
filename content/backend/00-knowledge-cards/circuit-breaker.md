---
title: "Circuit Breaker"
date: 2026-04-23
description: "說明下游持續失敗時如何暫停呼叫並保護系統"
weight: 29
---

Circuit breaker 的核心概念是「下游持續失敗時，暫時停止呼叫該下游」。它讓 application 快速失敗、使用 fallback 或進入降級，避免每個 request 都等待同一個壞掉的依賴。

## 概念位置

Circuit breaker 是失敗隔離工具。它通常搭配 timeout、retry、rate limit、fallback 與 observability 使用；目標是控制故障擴散，而非修復下游。

## 可觀察訊號與例子

系統需要 circuit breaker 的訊號是下游錯誤率高、latency 飆升，並拖慢上游服務。推薦服務持續 timeout 時，商品頁可以短暫停止呼叫推薦，改顯示熱門商品。

## 設計責任

Circuit breaker 要定義開啟條件、半開探測、恢復條件、fallback 行為與告警。設計時要控制短暫波動對可用性的影響，因此門檻與觀測資料要一起調整。
