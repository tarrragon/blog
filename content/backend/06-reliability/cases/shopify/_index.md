---
title: "Shopify"
date: 2026-05-01
description: "Shopify BFCM Scaling / Pod-based Isolation / Capacity Planning"
weight: 5
---

Shopify 是 BFCM（Black Friday / Cyber Monday）流量峰值的可靠性教學標竿、pod-based architecture 是 multi-tenant SaaS 的隔離典範。教學重點在「年度可預期峰值如何透過架構與演練準備」。

## 規劃重點

- Pod-based Architecture：多租戶切分、商家隔離設計
- BFCM 準備：年度峰值的 capacity planning 流程
- Resiliency Matrix：列舉服務與失效模式的對照表
- Toxiproxy / Resiliency tooling：Shopify 開源的 chaos 工具
- Database sharding：MySQL 分片策略與 online resharding

## 預計收錄實踐

| 議題                   | 教學重點                               |
| ---------------------- | -------------------------------------- |
| BFCM Capacity Planning | 容量預測、load test 設計、實際峰值對照 |
| Pod Architecture       | 多租戶切分、failure isolation          |
| Resiliency Matrix      | 失效模式對照表的維護方法               |
| Toxiproxy              | TCP-level 故障注入的工程實作           |
| Database resharding    | 線上 schema 與 sharding 變更           |

## 案例定位

Shopify 這個案例在講的是峰值流量如何被提前吸收，而不是在事故當下硬扛。讀者先抓 capacity planning、performance testing 與 pods architecture 的分工，再看它們怎麼把 BFCM 這種季節性壓力轉成可管理的工程節奏。

## 判讀重點

當流量會在短時間內暴增時，先做容量模型與壓測，再確認 pods 邊界能否切住故障擴散。當資料平台也在同一波壓力下成長時，重點不只在擴容，而在是否能保住查詢、寫入與回放的穩定節奏。

## 可操作判準

- 能否在 peak 之前說出容量上限與安全緩衝
- 能否把壓測結果對應到真實流量模型
- 能否讓 pods 邊界成為故障隔離單位
- 能否在高峰前完成演練與當日指揮節奏對齊

## 與其他案例的關係

Shopify 的價值在於它把峰值準備寫成年度節奏，這和 LinkedIn 的 capacity planning、AWS S3 的區域風險、Discord 的流量驚奇都能互相對照。讀這頁時要抓的是「先把峰值變成可預測問題」，而不是等事故來了才補救。

## 代表樣本

- BFCM 前的 capacity planning 讓峰值壓力先被模型吸收，而不是直接落在事故當下。
- pods architecture 把多租戶流量切成較小隔離單位，限制故障擴散。
- performance testing 讓真實峰值在演練階段就可見。
- resiliency tooling 讓團隊能在高峰前驗證失效模式。
- database resharding 讓高峰下的 stateful 系統仍能持續擴容。
- incident rehearsal 讓當日指揮與復原節奏先對齊。
- resiliency matrix 讓每個服務與失效模式都有明確對照。
- Toxiproxy 讓 TCP 層故障注入成為可重用工具。

## 引用源

- [Capacity Planning at Scale](https://shopify.engineering/capacity-planning-shopify)：BFCM 前的容量規劃與驗證方法。
- [Performance Testing At Scale—for BFCM and Beyond](https://shopify.engineering/scale-performance-testing)：BFCM scale testing 與壓測節奏。
- [A Pods Architecture To Allow Shopify To Scale](https://shopify.engineering/a-pods-architecture-to-allow-shopify-to-scale)：pods 架構與隔離設計。
- [How to Reliably Scale Your Data Platform for High Volumes](https://shopify.engineering/blogs/engineering/reliably-scale-data-platform)：資料平台在高流量下的可靠性方法。
