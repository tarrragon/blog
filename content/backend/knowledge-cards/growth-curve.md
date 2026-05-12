---
title: "Growth Curve"
date: 2026-05-12
description: "說明用戶 / 流量隨時間成長的五種典型形狀、影響容量規劃方法"
weight: 232
---

Growth curve 的核心概念是「用戶 / 流量隨時間成長的形狀分五類：linear、step、exponential、S-curve、cyclical」。不同形狀對應不同容量規劃方法、forecast 方式跟 headroom 比例。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 概念位置

- **Linear growth**：用戶月增 X%、B2B SaaS 常見、forecast 線性外推
- **Step growth**：每次行銷 / 活動跳一階、需要 event tier 規劃
- **Exponential growth**：早期初創、病毒擴散、forecast 容易低估
- **S-curve growth**：成熟產品、會 saturate、需要規劃 mature stage 容量
- **Cyclical**：電商季節性、Black Friday + Cyber Monday + Christmas

可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 可觀察訊號與例子

判讀 growth curve 的訊號是「過去 12 個月 MAU 圖形」。對應案例：[Zoom COVID](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) step growth（1000 萬 → 3 億）；[Pokemon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) exponential 之後可能 S-curve；[ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) cyclical。

## 設計責任

設計容量規劃節奏時、要先判讀 growth curve 形狀、再選 forecast 方法。Linear 適合每月 review；step 適合 *事件前後* review；exponential 適合每週 review；cyclical 適合按 cycle 規劃；S-curve 要規劃 maturation 後容量保持但成長放緩。curve 形狀變了（exponential 變 linear）也是策略訊號。
