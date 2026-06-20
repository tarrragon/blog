---
title: "模組七：突發流量應對"
date: 2026-06-20
description: "行銷活動、新聞曝光、產品上線 — 預期和非預期的流量高峰如何準備和應對"
weight: 7
tags: ["devops", "burst-traffic", "scaling", "queue", "degradation"]
---

回答「流量突然變成平常的 10 倍到 100 倍時怎麼辦」。預期高峰可以預先擴容，非預期高峰靠降級和緩衝。

## 待寫章節

- [ ] 預期高峰的準備（容量預估、預先擴容、warm-up、CDN 預快取）
- [ ] 非預期高峰的應對（自動擴縮、Queue 緩衝、動態取樣、降級模式）
- [ ] Queue 做突發緩衝（Kafka / NATS / Redis Streams — 和 backend/03 互補但聚焦 burst 場景）
- [ ] 降級決策（什麼功能先關、什麼功能最後關、降級的自動化 vs 手動決策）
- [ ] 高峰後的回復（queue 積壓消化、快取重建、資料補齊）

## 跨分類引用

- ← [monitoring 模組四 Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)：監控系統自身的突發流量應對
- → [devops 模組三 流量管控](/devops/03-traffic-management/)：流量管控是突發流量應對的基礎工具
- → [devops 模組五 容量規劃](/devops/05-capacity-planning/)：容量規劃決定「正常多少、高峰多少」
