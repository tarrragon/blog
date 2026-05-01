---
title: "Meta / Facebook"
date: 2026-05-01
description: "Meta Reliability Engineering 與超大規模事故學習"
weight: 23
---

Meta（前 Facebook）是超大規模分散式系統的代表、2021-10 BGP 全球失效事故是大規模事故敘事的教學標竿。Engineering blog 公開的 reliability 文章涵蓋 region failover、cell architecture 等深度實踐。

## 規劃重點

- BGP 與 DNS 自我封鎖：2021-10 事故揭露的內部依賴鎖死
- Region Failover：超大規模服務的跨區切換挑戰
- Cell Architecture：Facebook 規模下的 cell 設計
- Storm：Internal incident management 系統公開的設計

## 預計收錄實踐

| 議題                | 教學重點                            |
| ------------------- | ----------------------------------- |
| 2021-10 BGP 事故    | 配置變更鎖死自己、recovery 工具失效 |
| Region Failover     | 超大規模 traffic shift 的設計       |
| Storm IM System     | 內部 IR 工具的揭露                  |
| Reliability Reviews | 服務級可靠性審查制度                |

## 引用源

待補（Meta engineering blog、2021-10 post-mortem URL）。
