---
title: "4.7 Cardinality 治理與成本邊界"
date: 2026-05-01
description: "把 metric / log / trace 的 cardinality 與成本作為平台一級治理議題"
weight: 7
---

## 大綱

- cardinality 為何爆：unbounded label（user_id / request_id / url path）
- metrics 的 cardinality 影響：時序資料庫 series 爆炸、查詢退化
- log 的 cardinality 影響：索引膨脹、保留成本
- trace 的 [sampling](/backend/knowledge-cards/sampling/) 策略：head sampling vs tail sampling、tradeoff
- cost-aware observability：成本作為治理輸入而非事後賬單
- governance 控制面：label 白名單、ingestion quota、保留階梯
- 跟 [4.1 log schema](/backend/04-observability/log-schema/) 的分工：4.1 設計欄位、4.7 設邊界
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：4.2 是 metric 種類、4.7 是 label 治理
- 反模式：所有事件都打高 cardinality label、預算耗盡才砍訊號、保留策略無階梯

## 概念定位

Cardinality 治理是把觀測維度當成有限資源管理的流程，責任是讓訊號足夠可切分，同時不讓儲存、查詢與告警成本失控。

這一頁處理的是成本邊界。可觀測性需要有選擇地收集訊號；它把高價值維度留在可查詢路徑，把低價值或無界維度放到更合適的資料層。

## 核心判讀

判讀 cardinality 時，先看維度是否有決策價值，再看它是否有上界。

重點訊號包括：

- user id、request id、完整 URL 是否進入不該承受的 metric label
- log index 是否只索引常用查詢欄位
- trace [sampling](/backend/knowledge-cards/sampling/) 是否能優先保留高價值樣本
- [retention](/backend/knowledge-cards/retention/) 是否依資料熱度與法規責任分層

## 判讀訊號

- metric series 數量曲線陡升、TSDB 查詢退化
- log ingestion 成本月對月雙位數成長
- label 含 user_id / request_id / 完整 URL 直接送到 metric
- ingestion quota 觸發時靠砍訊號救火、無 graceful 降階
- 保留策略全平、無冷熱分層、舊資料拖累查詢

## 交接路由

- 04.6 SLI/SLO：SLI metric 的 cardinality 上限
- 06.9 容量成本：observability 成本作為容量規劃輸入
- vendors：各平台的 ingestion / query quota 模型
- 04.15 cost attribution：成本治理的責任分配層
