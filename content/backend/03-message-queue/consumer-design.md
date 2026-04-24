---
title: "3.4 consumer 設計與去重"
date: 2026-04-23
description: "整理 consumer、checkpoint 與 replay safety"
weight: 4
---

這一章聚焦在 [consumer](/backend/knowledge-cards/consumer/) 端怎麼做可重入、可重試、可回放的設計。

## 大綱

- [consumer group](/backend/knowledge-cards/consumer-group/) 與 [partition](/backend/knowledge-cards/partition/) / subscription
- [checkpoint](/backend/knowledge-cards/checkpoint/) 與 [offset](/backend/knowledge-cards/offset/)
- [idempotency](/backend/knowledge-cards/idempotency/) key
- replay safety
