---
title: "2.4 distributed lock 與租約"
date: 2026-04-23
description: "整理鎖語意、租約風險與適用場景"
weight: 4
---

## 大綱

- lock lease
- renewal / expiration
- split brain risk
- when to avoid distributed lock

## 相關語言章節

- [Go：高併發下的 Redis 讀寫邊界](../../go/06-practical/data-access-boundaries/)
