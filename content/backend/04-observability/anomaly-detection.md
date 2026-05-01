---
title: "4.14 Anomaly Detection"
date: 2026-05-01
description: "把 ML / statistical baseline 訊號跟 rule-based alert 整合"
weight: 14
---

## 大綱

- anomaly detection 跟 rule-based alert 的差異：rule 抓已知、anomaly 抓未知
- baseline 模型類別：seasonal、moving window、percentile、ML（forecast / clustering）
- 訊號處理：anomaly 是 hint、不是 page；常作為 dashboard widget 或低 severity alert
- false positive 治理：跟 rule-based alert 共用 noise budget
- explainability：anomaly fired 時要能定位到哪個維度
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的整合：anomaly 通常先進 dashboard、確認後升級 alert
- 跟 [4.6 SLI/SLO](/backend/04-observability/sli-slo-signal/) 的差異：SLO 是商業承諾、anomaly 是統計訊號
- vendor 取捨：Datadog Watchdog / New Relic AI / 自建 Prophet / Anomalo
- 反模式：anomaly 直接接 page、噪音爆量；anomaly 模型不可解釋；baseline 沒對齊季節性

## 判讀訊號

- alert 規則寫到爆、仍漏掉 novel failure mode
- 已知 anomaly 訊號被忽略、靠人工巡視 dashboard
- anomaly fired 後無人能解釋「為什麼異常」
- 模型未對齊週期性（週末 / 節慶 / promo）造成噪音
- 同一指標 anomaly + rule alert 重複觸發、無協調

## 交接路由

- 04.4 dashboard-alert：anomaly 升級 alert 的條件
- 04.6 SLI/SLO：跟 SLO burn rate 的訊號分工
- 04.8 訊號治理閉環：anomaly false positive 的淘汰
