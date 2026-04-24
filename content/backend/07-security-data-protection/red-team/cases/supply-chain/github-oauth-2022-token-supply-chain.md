---
title: "7.R7.2.2 GitHub OAuth 2022：第三方 token 供應鏈風險"
date: 2026-04-24
description: "第三方整合 token 被竊後，如何形成跨組織存取風險"
weight: 71722
---

## 事故摘要

2022 年 4 月，GitHub 公告指出攻擊者使用從第三方整合服務取得的 OAuth token 存取受影響組織資料。

## 攻擊路徑

1. 攻擊第三方整合節點。
2. 取得可用 OAuth token。
3. 使用 token 存取下游客戶資產。

## 失效控制面

- token 權限範圍過寬。
- token 生命周期偏長，撤銷速度慢。
- 整合關係資產盤點與監控不足。

## 如果 workflow 少一步會發生什麼

若缺少「第三方 token 全域盤點與快速撤銷」，事件發生後仍會留下可用 token，形成二次入侵窗口。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](../../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：採最小權限 token 與明確用途分域。
- 日常：建立第三方整合清單與失效期限巡檢。
- 事故中：依清單自動化撤銷、輪替、補授權。

## 可引用章節

- `backend/07-security-data-protection` 的憑證與授權治理
- `backend/04-observability` 的第三方整合監測

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[github.blog](https://github.blog/news-insights/company-news/security-alert-stolen-oauth-user-tokens/)
- 政府或監管：[github.blog](https://github.blog/2022-12-08-notice-of-security-incident/)
- 技術分析：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)
