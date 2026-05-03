---
title: "4.8 訊號治理閉環"
date: 2026-05-01
description: "把 postmortem 揭露的偵測缺口回寫成新訊號、讓觀測能力隨事故學習成長"
weight: 8
---

## 大綱

- 為何訊號需要治理閉環：alert / metric / dashboard 是會腐敗的資產
- 偵測缺口類別：訊號太晚、cardinality 不足、[symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) 缺、dashboard 無人看
- 從 [8.5 post-incident review](/backend/knowledge-cards/post-incident-review/) [action items](/backend/knowledge-cards/action-item-closure/) 回寫成新訊號
- 從 [6.4 chaos](/backend/knowledge-cards/chaos-test/) 揭露的觀測盲區補新 metric
- alert 健康度：noise rate、ack 時延、誤報率與 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)
- dashboard 健康度：訪問頻率、orphan dashboard 清理
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的分工：4.4 是設計、4.8 是維運與淘汰
- 跟 [8.11 閉環](/backend/08-incident-response/observability-reliability-incident-loop/) 的對應：4.8 是 04 端的閉環責任、8.11 是跨模組視角
- 反模式：alert 只增不減、dashboard 全是裝飾、[post-incident review](/backend/knowledge-cards/post-incident-review/) action items 永遠 open

## 概念定位

訊號治理閉環是把事故、演練與日常使用經驗回寫到觀測系統的流程，責任是讓 alert、metric 與 dashboard 隨服務變化而更新。

這一頁處理的是訊號生命週期。觀測資產會老化：服務拓撲會變、流量型態會變、告警接收者會變，因此每個訊號都需要新增、修訂與淘汰路徑。

## 核心判讀

判讀訊號治理時，先看缺口是否有來源，再看改善項是否真的關閉。

重點訊號包括：

- [post-incident review](/backend/knowledge-cards/post-incident-review/) 是否把偵測缺口轉成具體 metric / alert / dashboard 變更
- [chaos test](/backend/knowledge-cards/chaos-test/) 或 DR 演練是否暴露新的觀測盲區
- alert noise、ack time、false positive 是否有趨勢追蹤
- orphan dashboard 與過期 alert 是否有定期清理節奏

## 判讀訊號

- alert 數量只增不減、無淘汰流程
- alert noise rate > 50%、ack 後無實際動作
- dashboard 半年無人訪問、仍存在於主目錄
- [post-incident review](/backend/knowledge-cards/post-incident-review/) [action items](/backend/knowledge-cards/action-item-closure/) 大半 open > 90 天
- 同類事故重複發生、訊號層無更新

## 交接路由

- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：[action items](/backend/knowledge-cards/action-item-closure/) 回寫機制
- 06.4 [chaos test](/backend/knowledge-cards/chaos-test/)：實驗暴露觀測盲區
- 06.5 pre-mortem：預判訊號缺口
- 04.7 cardinality：新訊號的成本邊界
- 04.14 anomaly detection：anomaly false positive 的淘汰
