---
title: "模組二：快取與 Redis"
date: 2026-04-22
description: "整理快取策略、Redis 資料型別與分散式狀態輔助能力"
weight: 2
---

快取模組的核心目標是說明暫存資料如何提升讀取效率，同時不破壞 source of truth。語言教材會處理 cache port、資料複製邊界與 TTL 的程式邊界；本模組負責 Redis 與快取策略的具體實作。

## 暫定分類

| 分類             | 內容方向                                         |
| ---------------- | ------------------------------------------------ |
| Cache aside      | read-through 思路、cache miss、invalidation      |
| TTL 與 eviction  | 過期策略、容量控制、熱點資料                     |
| Redis data types | string、hash、set、sorted set、stream 的適用場景 |
| Presence store   | 即時連線狀態、過期清理、跨節點查詢               |
| Distributed lock | lock 語意、租約、失效與風險                      |
| Pub/Sub          | 即時通知、跨節點 fan-out、可靠性限制             |

## 與語言教材的分工

語言教材處理 interface / protocol、並發或非同步保護、timeout 與 cache 呼叫邊界。Backend cache 模組處理 Redis command、資料結構、失效策略、跨節點一致性與操作風險。

## 相關語言章節

- [Go：指標與資料複製邊界](../../go/02-types-data/pointers-copy/)
- [Go 進階：共享狀態與複製邊界](../../go-advanced/01-concurrency-patterns/shared-state/)
- [Go 進階：跨節點 WebSocket](../../go-advanced/07-distributed-operations/cross-node-websocket/)
