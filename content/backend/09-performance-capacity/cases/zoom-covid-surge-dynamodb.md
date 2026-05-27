---
title: "9.C18 Zoom：COVID 期間從 1000 萬到 3 億 DAU 的 30 倍突發"
date: 2026-05-12
description: "Zoom 在 2020 年 COVID 爆發時、日活從 1000 萬衝到 3 億、用 DynamoDB 撐住會議後端"
weight: 18
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "surge"]
---

這個案例的核心責任是說明「SaaS 類 surge」跟 [9.C8 Pokemon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) 的「product surge」差異。Zoom 的 30 倍成長不是「產品爆紅」、是「外部事件（COVID）逼全世界改變工作模式」、突發是 *結構性* 的、不是回歸均值的暫時現象。

## 觀察

Zoom 在 2020 年 COVID 期間的關鍵敘述（引自 [DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)）：

| 指標       | 數字                                             |
| ---------- | ------------------------------------------------ |
| 日活參與者 | 1000 萬 → 3 億（2020 年 3 月）                   |
| 成長倍數   | 30x                                              |
| 主資料層   | Amazon DynamoDB（會議 metadata）                 |
| 擴容描述   | 「nearly infinitely with no performance issues」 |

關鍵敘述：「On the backend, they were able to manage this surge with Amazon DynamoDB for Zoom Meetings.」

## 判讀

Zoom surge 揭露三個 SaaS 突發成長的工程重點。

1. **SaaS surge 是結構性、不是暫時性**：Pokemon GO 上線爆紅後流量會隨熱度消退、Zoom COVID 成長是「永久 baseline 上移」。容量規劃不能假設「過幾個月會回來」、必須假設「3 億 DAU 是新常態」。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的長期 baseline 重新校準。
2. **DynamoDB 「無限擴容」對 SaaS 元資料層特別適用**：Zoom 會議 metadata（room ID、participant list、permission state）是典型 KV 工作負載、partition key（meeting_id）天然均勻、不會 hot partition。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 同樣的 partition 均勻優勢。
3. **媒體串流不在 DynamoDB**：Zoom 的影音流量是 P2P + edge servers、不經 DynamoDB。DynamoDB 只承擔「control plane」、不承擔「data plane」。這個分離是擴 30 倍的前提 — 控制面跟資料面解耦、控制面用 managed 服務、資料面用專屬基礎設施。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的關鍵路徑切分。

需要警惕：「nearly infinitely」是行銷敘述、不是工程承諾。實務上 Zoom 在 COVID 初期確實遇到 outage 與性能問題、後續才穩定。讀案例時要看 *最終狀態* 跟 *過程中的 incident*。

## 策略

可重用的工程做法：

1. **控制面跟資料面分離**：高頻 metadata 操作放 managed KV（DynamoDB / Cosmos DB / Firestore）、大資料量串流放專屬基礎設施（CDN / WebRTC / 自管 servers）。對應 [05 部署平台模組](/backend/05-deployment-platform/) 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/)。
2. **surge 後重新校準 SLO baseline**：30x 成長之後、SLO 的「正常範圍」要更新、否則 monitoring 會誤報。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 SLO 演進。
3. **長期 surge 觸發架構重新評估**：DynamoDB 是「擴大量」的好選擇、但成本也跟著放大。當 baseline 從 1000 萬永久升到 3 億、原本的 on-demand 模式可能變得貴、要考慮 provisioned + auto-scaling 組合。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。

跨平台等效：Google Meet 也用 Spanner / Firestore、Microsoft Teams 用 Cosmos DB — 三家視訊會議都靠 managed KV 撐 metadata、是同一個架構模式的不同 vendor 實作。

## 下一步路由

- 對照 product surge → [9.C8 Pokemon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)
- 想理解 control plane vs data plane → [9.5 瓶頸定位流程](/backend/09-performance-capacity/) + [05 部署平台模組](/backend/05-deployment-platform/)
- 想規劃 surge 後的 SLO → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) + [04.16 SLI / SLO 訊號](/backend/04-observability/sli-slo-signal/)
- 想評估 surge 下的 on-demand vs provisioned 切換 → [DynamoDB on-demand vs provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)
- 想避免 surge 觸發 hot partition → [DynamoDB partition key 反模式](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)

## 引用源

- [Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
- [Zoom Video Communications on AWS](https://aws.amazon.com/solutions/case-studies/innovators/zoom/)
