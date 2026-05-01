---
title: "4.15 Cost Attribution / Chargeback"
date: 2026-05-01
description: "把 observability 成本拆到團隊、產品、環境維度"
weight: 15
---

## 大綱

- 為何需要 attribution：共享平台模式下、成本失控時無人擁有
- 拆分維度：team、service、environment、tenant、cost driver type（ingestion / retention / query）
- attribution 的訊號來源：metric label、log tag、span attribute
- chargeback vs showback：實際扣款 vs 透明化
- 跟 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的分工：4.7 是治理工具、4.15 是責任分配
- vendor 帳單拆分能力：Datadog usage attribution、Honeycomb teams、自建 cost dashboard
- 跟 [6.9 capacity-cost](/backend/06-reliability/capacity-cost/) 的整合：observability 成本作為總體成本的一部分
- 反模式：平台團隊吸收所有成本、產品團隊無 incentive 控制；attribution 顆粒度太粗、無法定位

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
