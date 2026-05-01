---
title: "Atlassian Statuspage"
date: 2026-05-01
description: "公開狀態頁 SaaS、Atlassian 出品"
weight: 7
---

Statuspage 是 Atlassian 收購整合的公開狀態頁 SaaS、提供 component / incident / scheduled maintenance / metrics 揭露、subscriber 通知（email / SMS / Slack / webhook）。是公開狀態頁的事實標準。

## 適用場景

- 對外公開服務狀態頁
- 需要 component-level 細粒度揭露
- Subscriber 通知（email / SMS / RSS）
- 跟 Opsgenie / PagerDuty / incident.io 整合

## 不適用場景

- 預算敏感（看 Instatus）
- OSS 偏好（看 Cachet）
- 簡單內部頁

## 跟其他 vendor 的取捨

- vs `instatus`：Statuspage 完整成熟；Instatus 輕量便宜現代 UI
- vs Cachet（OSS）：Statuspage SaaS；Cachet 自管
- vs FireHydrant 內建 status page：FireHydrant IR + 簡單 status；Statuspage 專業 status

## 預計實作話題

- Component / group 設計
- Incident template
- Scheduled maintenance
- Subscriber management
- API automation（從 IR 平台 push update）
- 自有 domain + branding
