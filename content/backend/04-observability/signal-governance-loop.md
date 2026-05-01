---
title: "4.8 訊號治理閉環"
date: 2026-05-01
description: "把 postmortem 揭露的偵測缺口回寫成新訊號、讓觀測能力隨事故學習成長"
weight: 8
---

## 大綱

- 為何訊號需要治理閉環：alert / metric / dashboard 是會腐敗的資產
- 偵測缺口類別：訊號太晚、cardinality 不足、symptom-based alert 缺、dashboard 無人看
- 從 [8.5 postmortem](/backend/08-incident-response/post-incident-review/) action items 回寫成新訊號
- 從 [6.4 chaos](/backend/06-reliability/chaos-testing/) 揭露的觀測盲區補新 metric
- alert 健康度：noise rate、ack 時延、誤報率
- dashboard 健康度：訪問頻率、orphan dashboard 清理
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的分工：4.4 是設計、4.8 是維運與淘汰
- 跟 [8.11 閉環](/backend/08-incident-response/observability-reliability-incident-loop/) 的對應：4.8 是 04 端的閉環責任、8.11 是跨模組視角
- 反模式：alert 只增不減、dashboard 全是裝飾、postmortem action items 永遠 open

## 判讀訊號

- alert 數量只增不減、無淘汰流程
- alert noise rate > 50%、ack 後無實際動作
- dashboard 半年無人訪問、仍存在於主目錄
- postmortem action items 大半 open > 90 天
- 同類事故重複發生、訊號層無更新

## 交接路由

- 08.5 postmortem：action items 回寫機制
- 06.4 chaos：實驗暴露觀測盲區
- 06.5 pre-mortem：預判訊號缺口
- 04.7 cardinality：新訊號的成本邊界
- 04.14 anomaly detection：anomaly false positive 的淘汰
