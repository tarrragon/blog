---
title: "Gaming：高峰流量下的訊號新鮮度與 Cardinality"
date: 2026-05-07
description: "在高峰事件中控制訊號延遲與維度爆炸，維持告警與定位可信度。"
weight: 2
---

本案例的核心責任是避免高峰流量讓觀測系統本身失真。若訊號延遲與 cardinality 膨脹失控，值班決策會落在過期資料上。

## 判讀訊號

| 訊號                     | 判讀重點               | 回寫章節                                                      |
| ------------------------ | ---------------------- | ------------------------------------------------------------- |
| ingestion lag            | 訊號是否延遲到不可決策 | [4.11](/backend/04-observability/telemetry-pipeline/)         |
| cardinality growth slope | 維度是否快速失控       | [4.7](/backend/04-observability/cardinality-cost-governance/) |
| alert freshness gap      | 告警是否反映當前狀態   | [4.17](/backend/04-observability/telemetry-data-quality/)     |

## 下一步路由

先定義高峰模式的 signal SLO，再用 [6.24](/backend/06-reliability/rule-rollout-safety-gate/) 對齊規則推送閘門。
