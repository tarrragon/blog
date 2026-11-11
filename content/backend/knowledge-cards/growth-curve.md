---
title: "Growth Curve"
date: 2026-05-12
description: "說明用戶 / 流量隨時間成長的五種典型形狀、影響容量規劃方法"
weight: 233
---

Growth curve 的核心概念是「用戶 / 流量隨時間成長的形狀分五類：linear、step、exponential、S-curve、cyclical」。不同形狀對應不同容量規劃方法、forecast 方式跟 headroom 比例。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 跟其他概念的關係

- **Linear growth**：用戶月增 X%、B2B SaaS 常見、forecast 線性外推
- **Step growth**：每次行銷 / 活動跳一階、需要 event tier 規劃
- **Exponential growth**：早期初創、病毒擴散、forecast 容易低估
- **S-curve growth**：成熟產品、會 saturate、需要規劃 mature stage 容量
- **Cyclical**：電商季節性、Black Friday + Cyber Monday + Christmas

可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 可觀察訊號與例子

判讀 growth curve 的訊號是「過去 12 個月 MAU 圖形」。對應案例：[Zoom COVID](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) step growth（1000 萬 → 3 億）；[Pokemon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) exponential 之後可能 S-curve；[ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) cyclical。

## 判斷條件與後果

容量規劃的 review 節奏與 forecast 方法取決於 growth curve 的形狀，原因是形狀決定了 forecast 的誤差多快累積到超出 headroom。Linear growth 每月的增量相近，每月 review 就看得到偏離；step growth 的增量集中在行銷或活動前後，review 排在事件前後才量得到那一階的跳升；exponential growth 的增量每期放大，線性外推會低估，所以 review 縮到每週；cyclical 的峰值隨週期重複，按 cycle 規劃比按月平均更接近實際峰值；S-curve 在成熟之後成長放緩，規劃的對象從追加容量轉為維持既有容量。形狀本身也會改變（exponential 轉成 linear），這時原本的 review 節奏與 forecast 方法跟著失準，所以形狀的改變也是調整容量策略的訊號。
