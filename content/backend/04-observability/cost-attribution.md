---
title: "4.15 Cost Attribution / Chargeback"
date: 2026-05-01
description: "把 observability 成本拆到團隊、產品、環境維度"
weight: 15
---

## 大綱

- 為何需要 attribution：共享平台模式下、成本失控時無人擁有
- 拆分維度：team、service、environment、tenant、cost driver type（ingestion / [retention](/backend/knowledge-cards/retention/) / query）
- attribution 的訊號來源：metric label、log tag、span attribute
- chargeback vs showback：實際扣款 vs 透明化
- 跟 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的分工：4.7 是治理工具、4.15 是責任分配
- vendor 帳單拆分能力：Datadog usage attribution、Honeycomb teams、自建 cost dashboard
- 跟 [6.9 capacity-cost](/backend/06-reliability/capacity-cost/) 的整合：observability 成本作為總體成本的一部分
- 反模式：平台團隊吸收所有成本、產品團隊缺少 incentive 控制；attribution 顆粒度太粗、定位成本來源需要人工拆帳

## 概念定位

Cost attribution 是把 observability 成本拆回團隊、服務、環境與成本來源的治理能力，責任是讓使用訊號的人也看見訊號成本。

這一頁處理的是責任分配。Cardinality governance 能控制技術成本，attribution 讓組織知道成本由誰產生、服務於什麼目的、是否值得保留。

## 核心判讀

判讀 cost attribution 時，先看成本是否能對應服務，再看 [ownership](/backend/knowledge-cards/ownership/) 是否能採取行動。

重點訊號包括：

- ingestion、retention、query 是否能分開歸因
- team / service / environment label 是否穩定
- showback 是否足以改變行為，或需要 chargeback
- 高成本訊號是否能對應事故、SLO 或除錯價值

## 判讀訊號

- 成本季度增長、無人能說「哪個團隊 / 服務在燒」
- 高成本服務跟高價值服務不對應、無 ROI 視角
- 平台團隊背所有預算、產品團隊把 observability 當免費資源
- attribution dashboard 存在但無 owner、半年沒看
- vendor 帳單只有總額、無服務級拆分

## 交接路由

- 04.7 cardinality / cost：成本治理的工具層
- 04.11 telemetry pipeline：pipeline 各層的成本歸屬
- 06.9 capacity / cost：跟整體容量規劃對齊
