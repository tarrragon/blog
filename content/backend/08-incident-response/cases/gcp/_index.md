---
title: "Google Cloud Platform"
date: 2026-05-01
description: "GCP 重大事故時間線與架構脈絡"
weight: 4
---

GCP 是全球 anycast + 強控制面整合的代表、Load Balancer / IAM 失效是全球控制面事故的教學標竿。Google 公開的 post-mortem 包含詳細時間線與技術細節、適合作為事故敘事範本。

## 規劃重點

- 全球控制面失效：IAM / Load Balancer 失效如何擴散到所有地區
- 配置變更的 blast radius：staged rollout 為何在 L7 LB 變更上難以實施
- Postmortem 結構：Google PIR 的 timeline / impact / root cause / action items 格式
- 跨服務依賴：Cloud SQL / GKE / Cloud Build 之間的隱性耦合

## 預計收錄事故

| 年份 | 事故                       | 教學重點                                    |
| ---- | -------------------------- | ------------------------------------------- |
| 待補 | Load Balancer 全球失效     | 控制面變更 staged rollout 的限制            |
| 待補 | IAM / Identity 全球失效    | Identity 控制面是 single point of cascading |
| 待補 | YouTube / Drive 等下游退化 | 跨產品的 dependency 暴露                    |

## 引用源

待補（Google Cloud Status / Public Issue Tracker / SRE Book post-mortem）。
