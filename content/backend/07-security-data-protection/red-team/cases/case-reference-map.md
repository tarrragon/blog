---
title: "7.R7.M 案例引用地圖（服務主題 -> 案例 -> workflow）"
date: 2026-04-24
description: "用一張地圖把服務設計主題快速對應到事故案例與流程檢查點"
weight: 7179
---

## 引用地圖

| 服務主題 | 優先引用案例 | workflow 檢查點 |
| --- | --- | --- |
| 認證與權限邊界 | Uber 2022、Twilio 2022、MGM 2023 | 高風險操作 step-up、異常身分隔離、分級升級 |
| 第三方整合與 token | GitHub OAuth 2022、Okta/Cloudflare 2023 | token 分域、事件觸發輪替、供應商事件 playbook |
| CI/CD 與 secrets | CircleCI 2023、SolarWinds 2020、XZ 2024 | secrets 分級輪替、交付鏈驗證、版本凍結流程 |
| 邊界設備與外網入口 | MOVEit 2023、Ivanti 2024、PAN-OS 2024、Citrix 2023 | 入口隔離、分區修補、修補後狀態驗證 |
| 資料平台與外送風險 | Snowflake 2024、LastPass 2022、Mailchimp 2023 | 強制 MFA、匯出監控、高風險工具二次核准 |
| 營運連續性與回復 | Change Healthcare 2024、MGM 2023 | RTO/RPO、降級/切換演練、跨部門通訊節奏 |

## 寫作規則

1. 每個服務實例至少引用一個同類型事故案例。
2. 每個案例至少落地一個 workflow 步驟到 runbook。
3. 每個 runbook 必須對應可驗證量測（例如 MTTR、告警到升級時間）。

