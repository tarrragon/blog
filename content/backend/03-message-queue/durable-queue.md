---
title: "3.2 durable queue 與重試策略"
date: 2026-04-23
description: "整理持久化佇列、DLQ 與重試流程"
weight: 2
---

這一章把 [queue](../../knowledge-cards/queue/) 的持久化語意、重試與 dead-letter flow 拆開，方便後續連到 outbox 與 [consumer](../../knowledge-cards/consumer/) 設計。

## 大綱

- durable vs ephemeral queue
- retry、backoff、[jitter](../../knowledge-cards/jitter/)
- [dead-letter queue](../../knowledge-cards/dead-letter-queue/)
- ordering 與 [requeue](../../knowledge-cards/requeue/) 風險
