---
title: "Amazon"
date: 2026-05-01
description: "Amazon Cell-based Architecture / Shuffle Sharding / Blast Radius 設計"
weight: 3
---

Amazon 是 cell-based architecture 與 shuffle sharding 的代表、AWS Builders' Library 是大規模分散式系統的工程實踐 SSoT。教學重點在「如何設計才能讓失效局部化」。

## 規劃重點

- Cell-based Architecture：把服務切成獨立 cell、每個 cell 有完整 stack
- Shuffle Sharding：客戶請求映射到 cell 的隨機切分、讓單一壞客戶無法擊倒所有 cell
- Static Stability：control plane 失效時 data plane 仍能服務
- Constant Work Pattern：avoid scaling traffic in failure modes
- AWS Builders' Library：可重用 reliability patterns 的官方文件

## 預計收錄實踐

| 議題                     | 教學重點                                          |
| ------------------------ | ------------------------------------------------- |
| Cell-based Architecture  | DynamoDB / Route 53 / S3 的 cell 劃分原則         |
| Shuffle Sharding         | 數學上的 blast radius 量化                        |
| Static Stability         | control / data plane 分離的設計取捨               |
| Workload Isolation       | tenancy / region / availability zone 的隔離層級   |
| Build with constant work | 為何 push-based 比 pull-based 在 failure 時更穩定 |

## 引用源

待補（AWS Builders' Library URL、re:Invent 演講、AWS re:Post engineering blog）。
