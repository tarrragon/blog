---
title: "Retry Storm"
date: 2026-04-23
description: "說明大量重試如何把局部故障放大成系統壓力"
weight: 47
---


Retry storm 的核心概念是「大量 client 或 worker 在故障期間同時重試，導致下游壓力急速放大」。重試本來用來提高成功率，但在高流量下可能把暫時性故障變成持續過載。 可先對照 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)。

## 概念位置

Retry storm 是 retry policy、timeout、backoff、jitter 與 rate limit 的共同風險。每一層服務若都自動重試，單一使用者 request 可能變成多倍下游呼叫。 可先對照 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)。

## 可觀察訊號與例子

系統需要防止 retry storm 的訊號是下游錯誤率上升後，request 數、連線數與 CPU 同步上升。付款 API 短暫變慢時，所有 checkout instance 同時重試，可能讓付款 API 更難恢復。

## 設計責任

Retry storm 防護要包含重試預算、backoff、jitter、rate limit、circuit breaker 與告警。Runbook 應能看出原始流量與重試流量的比例。
