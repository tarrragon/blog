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

## 引用源

待補（Shopify Engineering blog URL、BFCM retrospectives、Resiliency Matrix 文件）。
