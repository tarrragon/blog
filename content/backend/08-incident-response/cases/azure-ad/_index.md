---
title: "Azure AD / Entra ID"
date: 2026-05-01
description: "Microsoft Identity 控制面失效與 cascading 影響"
weight: 14
---

Azure AD（現 Entra ID）是 Microsoft 生態的 identity 控制面、其失效會讓所有依賴 SSO 的服務無法登入、是 identity-as-cascading-point 的代表。

## 規劃重點

- Identity 控制面 single point of cascading：SSO 失效擴散到所有下游
- 配置變更 staged rollout 的限制：identity 服務難以 region-staged
- Token cache 緩衝：客戶端 token 有效期決定 outage 感受時間
- 跨產品依賴：M365 / Teams / GitHub Enterprise 等的隱性依賴

## 預計收錄事故

| 年份 | 事故                | 教學重點                                |
| ---- | ------------------- | --------------------------------------- |
| 2020 | 多次全球登入失效    | Identity cascading、staged rollout 限制 |
| 2021 | DNS / token service | Identity 服務的 sub-component 風險      |

## 引用源

待補（Microsoft post-incident report、Azure status history）。
