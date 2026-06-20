---
title: "模組五：容量規劃與壓力測試"
date: 2026-06-20
description: "要準備多少資源才夠 — 壓力測試方法、峰值估算、成本模型、規模拐點的判斷"
weight: 5
tags: ["devops", "capacity-planning", "load-testing", "peak-estimation", "cost-model"]
---

回答「要準備多少資源才夠、多的時候怎麼加、少的時候怎麼省」。容量規劃的輸入是流量模型，輸出是資源規格和成本。

## 待寫章節

- [ ] 流量模型建立（平均 / 峰值 / burst 的估算方法）
- [ ] 壓力測試工具和方法（k6 / wrk / locust — 測什麼、怎麼測、結果怎麼讀）
- [ ] 峰值估算（行銷活動的倍率、歷史峰值的安全係數）
- [ ] 成本模型（資源規格 × 使用時間 × 計費模式 — reserved / on-demand / spot）
- [ ] 規模拐點判斷（什麼訊號代表該擴容、什麼訊號代表可以縮容）
- [x] 容器化資源設計（memory / CPU / 磁碟限制、overlay fs、health check）

## 跨分類引用

- → [backend 效能容量](/backend/09-performance-capacity/)：Backend 的效能基準和容量估算
- → [devops 模組七 突發流量](/devops/07-burst-traffic/)：突發流量的容量預備
