---
title: "模組七：突發流量應對"
date: 2026-06-20
description: "行銷活動或新聞曝光帶來 10x-100x 流量時怎麼撐 — 突發分類、降級策略、queue 緩衝、規模分級應對"
weight: 7
tags: ["devops", "burst-traffic", "degradation", "queue", "scaling"]
---

回答「流量突然暴增時怎麼不掛」。突發流量和穩定高流量的處理策略不同 — 突發有時間限制，撐過去就恢復正常。

## 待寫章節

- [x] 突發流量的分類（可預期 vs 不可預期、持續時間和倍率）
- [x] 降級策略（動態取樣、事件優先級、功能降級、聚合前移）
- [x] Queue 緩衝（Kafka / NATS / Redis Streams 做 burst buffer）
- [x] 規模分級應對表（自用 → 中型 → 大型 → 商業網站）

## 跨分類引用

- ← [devops 模組三 流量管控](/devops/03-traffic-management/)：背壓和 rate limit 是突發應對的基礎元件
- → [monitoring 模組四 Collector](/monitoring/04-collector/)：Collector 的 ingestion scaling 是本模組的應用場景
- → [backend 非同步佇列](/backend/03-message-queue/)：Queue 的選型和操作實務
- → [devops 模組五 容量規劃](/devops/05-capacity-planning/)：預期突發的容量預備
- → [端到端資料完整性](/monitoring/04-collector/data-integrity/)：被自己 SDK DDoS 的三種場景
