---
title: "IAM（Identity and Access Management）"
date: 2026-06-26
description: "雲端平台的授權系統，回答「某個身分能不能對某個資源做某件事」"
weight: 14
tags: ["infra", "knowledge-cards", "iam", "security"]
---

IAM（Identity and Access Management）是雲端平台用來回答「某個身分能不能對某個資源做某件事」的授權系統。它把授權拆成三個獨立的元件：identity（身分，發起動作的主體）、policy（政策，描述「允許或拒絕對哪些資源做哪些動作」的規則）、role（角色，一組可以被臨時取得的權限集合，常見透過 [OIDC](/infra/knowledge-cards/oidc/) 換發短期憑證）。這三者的分工是後面所有憑證決策的前提。

## 概念位置

IAM 是[模組二：身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)的核心機制。它決定了誰能動什麼——人、服務、CI pipeline 各拿剛好夠用的權限（最小權限），憑證有明確的生命週期。身分層失守的代價在五個 infra 責任面向中最高，因為它是其他所有資源的閘門。

在 infra 系列中，IAM 的設計從三個維度展開：最小權限的持續收斂（不是一次設定就結束）、用 [OIDC](/infra/knowledge-cards/oidc/) 短期憑證取代長期 access key、以及跨帳號的權限邊界（SCP + Permissions Boundary）。

## 可觀察訊號

IAM 需要關注的訊號：某個 role 的 policy 有 `*:*` 或 `AdministratorAccess`（權限過大）；credential report 顯示有長期 access key 超過 90 天未輪替（憑證散落風險）；Access Analyzer 顯示某個 role 的實際使用 action 遠少於授予的 action（權限擴散）；dev 環境的 CI role 能列出 production 的資源（環境隔離失效）。

## 設計責任

IAM 設計時要決定：

- 身分類型區分：人用 SSO 登入（強制 MFA）、雲上服務用 instance profile / task role、雲外 CI 用 OIDC 聯合
- 權限分級：admin / operator / viewer 三級，見[團隊權限分級](/infra/02-identity-credentials/team-access-management/)
- 環境隔離：每個環境的 role 不能存取其他環境的資源
- 收斂節奏：定期用 Access Analyzer 觀察實際使用的 action，收掉沒用到的權限

## 鄰卡

- [OIDC](/infra/knowledge-cards/oidc/) — 用短期 token 取代長期 access key 的聯合機制
- [Security Group](/infra/knowledge-cards/security-group/) — 網路層的存取控制（IAM 是 API 層的存取控制）
- [CloudTrail](/infra/knowledge-cards/cloudtrail/) — 記錄 IAM 身分的 API 呼叫歷史
