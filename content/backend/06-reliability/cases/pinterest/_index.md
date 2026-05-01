---
title: "Pinterest"
date: 2026-05-01
description: "Pinterest Capacity Planning 與儲存架構可靠性"
weight: 22
---

Pinterest 是視覺探索平台、capacity planning 與儲存架構的工程文章揭露大規模 data-heavy service 的可靠性挑戰。

## 規劃重點

- Storage Capacity：HBase / TiDB 等 stateful 系統的 capacity model
- Cache Strategies：Memcache / Redis 大規模部署的 failure mode
- Scaling Patterns：visual search 等高運算服務的可靠性
- Migration Reliability：跨 storage backend migration 的零事故設計

## 預計收錄實踐

| 議題                  | 教學重點                             |
| --------------------- | ------------------------------------ |
| Storage Migration     | HBase → TiDB 等大規模 migration 設計 |
| Cache Reliability     | hot key、thundering herd 的工程處理  |
| Capacity Planning     | data-heavy service 的容量預測        |
| ML Serving Resilience | 推薦系統的可靠性需求                 |

## 引用源

待補（Pinterest engineering blog URL）。
