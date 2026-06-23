---
title: "GitHub Actions：Environment Protection 與 OIDC Cloud Auth"
date: 2026-06-23
description: "用 environment protection rules 做 deploy approval gate、用 OIDC 取代 long-lived cloud credential。"
weight: 2
tags: ["backend", "reliability", "vendor", "ci"]
---

## 問題情境

CI pipeline 的可靠性驗證在測試階段結束後，還需要兩道控制面才算完整。第一道是 deploy approval gate — 決定誰可以核准 production deploy、在什麼條件下放行。第二道是 credential 安全 — deploy 需要 cloud credential，但 long-lived secret 存在 CI 環境中會擴大洩漏面。

GitHub Actions 用 environment protection rules 處理第一道，用 OIDC federation 處理第二道。兩者搭配讓 deploy 流程同時滿足 [6.8 release gate](/backend/06-reliability/release-gate/) 的放行控制與 [07 資安](/backend/07-security-data-protection/) 的 credential 最小暴露原則。

## Environment Protection Rules

Environment 是 GitHub Actions 的 deploy 分層單位。每個 environment（staging / canary / production）可以獨立設定 protection rules，讓不同風險等級的 deploy 走不同的放行流程。

### Protection rule 類型

| 規則                     | 責任                                      | 典型設定                           |
| ------------------------ | ----------------------------------------- | ---------------------------------- |
| Required reviewers       | 指定人員核准後才能 deploy                 | production 需 2 人核准             |
| Wait timer               | deploy 前強制等待，讓最後一刻能攔住       | production 等 15 分鐘              |
| Deployment branch policy | 只允許特定 branch deploy 到該 environment | production 只接受 main / release/* |

Required reviewers 是 deploy 層的 release gate。當 workflow job 標記 `environment: production`，GitHub 會暫停 job 直到指定 reviewer 核准。reviewer 的選擇應對齊服務 ownership — 由該服務的 on-call lead 或 tech lead 核准，避免核准權過於集中或分散。

Wait timer 提供一個緩衝窗口。deploy 前等待 N 分鐘讓團隊有時間檢查 staging 結果、確認沒有進行中的事故、或在發現問題時取消 deploy。timer 長度跟服務風險等級對齊 — 低風險服務可以 0 分鐘，交易路徑可以 15-30 分鐘。

Deployment branch policy 限制哪些 branch 可以觸發特定 environment 的 deploy。這防止 feature branch 意外 deploy 到 production。production 通常只接受 main 或 release branch。

### 分層建議

staging 用自動 deploy — push 到 staging branch 直接觸發 workflow，無需 approval，回饋速度最大化。production 用 required reviewer + wait timer — 確保每次 production deploy 都經過人工確認與緩衝。canary 介於兩者之間 — 可以自動 deploy 但加 wait timer，讓觀測指標有時間反映。

## OIDC Cloud Auth

### Long-lived credential 的風險

CI deploy 需要 cloud credential（AWS access key / GCP service account key / Azure service principal）。傳統做法是把這些 credential 存在 GitHub repository secret 或 environment secret 中。long-lived credential 的風險在於：洩漏後攻擊者可以長期使用、rotation 需要手動更新 CI 設定、credential scope 常設得比實際需求更大。

### OIDC federation 的運作方式

GitHub Actions 支援作為 OIDC identity provider。workflow 在執行時可以向 GitHub 請求一個 short-lived OIDC token，cloud provider 信任這個 token 後發出 short-lived cloud credential。整個流程不需要在 CI 環境中存放任何 long-lived secret。

流程：workflow 啟動 → 向 GitHub OIDC provider 請求 token → token 帶有 repo / branch / environment 等 claim → cloud provider 的 trust policy 驗證 claim → 發出 short-lived credential（通常 1 小時有效期）。

### Cloud provider 配置

**AWS**：在 IAM 設定 OIDC identity provider（issuer: `token.actions.githubusercontent.com`）、建立 IAM role 並設定 trust policy 限制 repo + branch + environment。workflow 中用 `aws-actions/configure-aws-credentials` action 取得 session credential。

**GCP**：設定 Workload Identity Federation pool + provider、建立 service account 並綁定 pool。workflow 中用 `google-github-actions/auth` action 取得 short-lived token。

**Azure**：在 Azure AD 設定 federated credential 給 app registration、限制 repo + branch + environment。workflow 中用 `azure/login` action。

### Trust policy 的安全邊界

OIDC trust policy 必須限制到特定 repo、branch 與 environment。trust policy 寫成 wildcard（信任整個 GitHub org 的所有 repo）等於讓 org 內任何 repo 的 workflow 都能取得 cloud credential。最小權限原則：production environment 的 trust policy 只信任 `repo:org/service:environment:production`，不信任其他 environment 或 branch。

## 實作範例

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/staging-deploy
          aws-region: ap-northeast-1
      - run: ./scripts/deploy.sh staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/production-deploy
          aws-region: ap-northeast-1
      - run: ./scripts/deploy.sh production
```

staging job 自動觸發。production job 等 staging 完成後暫停，等待 environment protection rules 中設定的 reviewer 核准。兩個 job 各自用不同的 IAM role，scope 分離。

Environment secret 與 repository secret 的差異：environment secret 只在該 environment 的 job 中可用。把 production-only 的設定（如 database connection string）存在 production environment secret 而非 repository secret，避免 staging workflow 意外存取 production 資源。

## 邊界與陷阱

Environment protection rules 在 private repo 上需要 GitHub Team 或 Enterprise 方案。Free 方案的 private repo 無法使用 required reviewers 與 wait timer，只有 public repo 或付費方案可用。

OIDC trust policy 的常見錯誤是 subject claim 設定太寬。`sub` claim 的格式是 `repo:{owner}/{repo}:environment:{name}`（使用 environment 時）或 `repo:{owner}/{repo}:ref:refs/heads/{branch}`（不使用 environment 時）。用 wildcard match 或省略 environment 限制會讓非預期的 workflow 取得 credential。

Wait timer 設定要跟服務風險等級對齊。所有服務統一用 30 分鐘 wait timer 會拖慢低風險服務的 deploy velocity。對齊方式：低風險服務 0 分鐘、中風險 5-10 分鐘、高風險（交易路徑）15-30 分鐘。

Required reviewer 數量跟團隊大小對齊。只有 1 個 reviewer 等於沒有四眼原則；需要 5 個 reviewer 會造成 approval 排隊。2-3 個 reviewer 是多數團隊的平衡點。

## 整合路由

- 上游：[6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)（CI gate 通過後才進入 deploy 階段）
- 下游：[6.8 release gate](/backend/06-reliability/release-gate/)（environment protection 是 deploy 層的 release gate）
- 下游：[6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/)（deploy 結果作為 release evidence）
- 平行：[CircleCI](/backend/06-reliability/vendors/circleci/) contexts + approval jobs（同類功能的不同實作）
- 案例回寫：[Microsoft 變更分層](/backend/06-reliability/cases/microsoft/change-management-and-reliability-governance/)（變更風險分層對應 environment 分層）、[Google Error Budget](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)（error budget 消耗時提高 gate 門檻 → 可動態調整 required reviewer 數量）
