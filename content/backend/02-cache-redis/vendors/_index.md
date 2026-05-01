---
title: "快取 Vendor 清單"
date: 2026-05-01
description: "後端快取實作時的常用選擇，預先建立引用路徑"
weight: 90
---

本清單列出 backend 服務實作會選用的 cache vendor / platform。每個 vendor 一個資料夾，先建定位與取捨骨架。

## T1 vendor

- [redis](/backend/02-cache-redis/vendors/redis/) — OSS / Redis Stack、cache 主流
- [valkey](/backend/02-cache-redis/vendors/valkey/) — Redis fork、Linux Foundation 託管
- [memcached](/backend/02-cache-redis/vendors/memcached/) — 純 cache、無持久化
- [dragonflydb](/backend/02-cache-redis/vendors/dragonflydb/) — 高效能 Redis 相容替代
- [aws-elasticache](/backend/02-cache-redis/vendors/aws-elasticache/) — managed Redis / Memcached

## 後續擴充

- T2 候選：hazelcast、aerospike、keydb、garnet、momento
- T3 候選：caffeine（local cache）、varnish（HTTP cache）
