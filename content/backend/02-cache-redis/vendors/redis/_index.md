---
title: "Redis"
date: 2026-05-01
description: "OSS in-memory data structure store、cache 主流"
weight: 1
---

Redis 是 in-memory data structure store、cache 場景事實標準、支援豐富 data types（string / hash / list / set / sorted set / stream / hyperloglog / geo）。從 2024 起授權變動為 RSALv2 / SSPL（OSI 不認）、引發 Valkey fork。

## 適用場景

- 通用快取（cache-aside、read-through）
- Session store / rate limit counter / leaderboard
- Pub/Sub（小規模）/ Streams
- Distributed lock（含 Redlock 取捨）
- Presence store

## 不適用場景

- 持久性 source-of-truth（雖支援 AOF/RDB 但不適合）
- 大型訊息佇列（Streams 有極限、用 Kafka）
- 容量超過記憶體成本可承受

## 跟其他 vendor 的取捨

- vs `valkey`：fork 自 Redis 7.2.4、API 相容、授權自由
- vs `memcached`：Redis 有持久化與 data types；Memcached 純 cache 更輕量
- vs `dragonflydb`：DragonflyDB 多核效能更高但部分相容性差距

## 預計實作話題

- Cluster vs Sentinel
- AOF / RDB 持久化策略
- Eviction policy（LRU / LFU / random）
- Redis Modules（RedisJSON / Search / TimeSeries）
- 授權變動下的選擇
