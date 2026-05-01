---
title: "AWS ElastiCache"
date: 2026-05-01
description: "AWS managed Redis / Valkey / Memcached"
weight: 5
---

ElastiCache 是 AWS managed cache 服務、支援 Redis / Valkey / Memcached engine、託管 cluster mode、自動 failover、跨 AZ 複製。是 AWS 生態下 cache 的預設選擇。

## 適用場景

- AWS 生態服務需要 managed cache
- 需要跨 AZ 高可用、自動 failover
- 不想自管 Redis / Valkey cluster

## 不適用場景

- 跨雲需求
- 需要 Redis Stack 完整 modules（部分不支援）
- 極端成本敏感（managed premium）

## 跟其他 vendor 的取捨

- vs 自管 Redis / Valkey：託管成本 vs 運維彈性
- vs ElastiCache Serverless：on-demand 變體
- vs MemoryDB（AWS）：MemoryDB 是 durable Redis-compatible、定位介於 cache 與 DB 之間

## 預計實作話題

- Cluster mode enabled vs disabled
- Auto failover 機制
- Snapshot / backup 策略
- ElastiCache Serverless 適用判斷
- 從自管遷移路徑
