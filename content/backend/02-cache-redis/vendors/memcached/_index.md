---
title: "Memcached"
date: 2026-05-01
description: "純記憶體 key-value cache、無持久化"
weight: 3
---

Memcached 是最早期、最純粹的 in-memory cache、僅支援 string key-value、無持久化、無複雜 data types。極輕量、運維成本低、適合純 cache 場景。

## 適用場景

- 純 cache、不需要持久化
- 簡單 key-value、不需要 data types
- 多執行緒架構（vs Redis 早期單執行緒）
- 嚴格純 cache 邊界、避免誤用為 source-of-truth

## 不適用場景

- 需要 data types（list / hash / sorted set）
- 需要 pub/sub / streams
- 需要持久化 / 半持久化
- 需要 distributed lock

## 跟其他 vendor 的取捨

- vs `redis` / `valkey`：Memcached 純粹簡單；Redis / Valkey 功能豐富但更易誤用
- vs local cache（caffeine）：Memcached 跨節點共享；local cache 受限於 process

## 預計實作話題

- Consistent hashing 客戶端 sharding
- Slab allocator 與 memory fragmentation
- Multi-threaded scaling
- AWS ElastiCache for Memcached
