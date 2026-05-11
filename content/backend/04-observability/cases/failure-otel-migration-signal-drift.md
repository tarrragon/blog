---
title: "4.C9 反例：OTel 遷移後訊號漂移"
date: 2026-05-07
description: "雙軌採集未對齊導致告警與 SLO 判讀失真。"
weight: 9
tags: ["backend", "observability", "case-study"]
---

這個反例的核心責任是說明 observability 遷移失敗常不是資料丟失，而是語意漂移。

## 事故長相

OTel 切換後，儀表板看起來都有資料，但 on-call 開始收到不同告警，SLO burn rate 與舊系統長期對不上。同一個事故在新舊管線裡被歸到不同 service、不同 label 或不同 latency bucket。

## 為什麼會擴大

觀測資料是事故判讀的入口。若 metric 名稱、label、sampling、aggregation 不一致，團隊會對同一個現象做出不同判斷，甚至在錯誤訊號上回退服務。

## 回退判讀

觀測遷移的回退不一定是回到舊 agent。更重要的是保留新舊訊號對照，先停止讓新管線主導告警與 SLO 判定，再修正語意對齊。若直接關掉新管線，反而會失去分析漂移原因的證據。

## 觀測專屬告警條件

- 新舊管線對同一服務的 error rate 長期偏離
- missing span 或 missing metric 比例持續上升
- alert 噪音增加，但事故量沒有對應增加

## 下一步路由

回 [4.17](/backend/04-observability/telemetry-data-quality/) 與 [4.11](/backend/04-observability/telemetry-pipeline/)。
