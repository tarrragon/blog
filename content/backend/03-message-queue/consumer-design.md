---
title: "3.4 consumer 設計與去重"
date: 2026-04-23
description: "整理 consumer、checkpoint 與 replay safety"
weight: 4
---

這一章聚焦在 consumer 端怎麼做可重入、可重試、可回放的設計。

## 大綱

- consumer group 與 partition / subscription
- checkpoint 與 offset
- idempotency key
- replay safety

## 相關語言章節

- [Go 進階：多來源 event 融合](../../go-advanced/04-architecture-boundaries/event-fusion/)
- [Go 進階：事件去重邏輯的重構策略](../../go/07-refactoring/dedup-refactor/)
