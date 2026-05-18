---
title: "GitHub Actions"
date: 2026-05-01
description: "GitHub 原生 CI/CD、PR check、deploy gate"
weight: 1
tags: ["backend", "reliability", "vendor"]
---

GitHub Actions 是 GitHub 原生的 CI/CD 工具、承擔三個責任：PR check workflow（test / lint / coverage）、release 自動化 + environment protection rules、跨 platform matrix testing。設計取捨偏向「跟 GitHub 深度整合 + marketplace action 生態 + OIDC 認證雲端 + self-hosted runner」、是 GitHub-hosted 專案的預設 CI 選擇。

## 本章目標

讀完本章後、你應該能：

1. 寫 workflow（.github/workflows/*.yml）
2. 設計 PR check + matrix testing
3. 用 reusable workflows / composite actions 復用
4. 配置 environment protection + approval gate
5. 用 OIDC + cloud auth（無 long-lived secret）

## 最短路徑：5 分鐘把 GitHub Actions 跑起來

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
```

## 日常操作與決策形狀

### Workflow 設計

子議題：

- on triggers（push / pull_request / schedule / workflow_dispatch / repository_dispatch）
- job / step / action
- Matrix（OS / language version / test split）
- 對應指令範例：`gh workflow run`、`gh run list`

### Cache 策略

子議題：

- actions/cache（語言依賴 / build cache）
- Cache key 設計（hashFiles + version）
- Cache scope（per branch / per repo）
- 對應 build speed optimization

### Reusable workflows / composite actions

子議題：

- Reusable workflow：跨 repo 引用整個 workflow
- Composite action：把多 step 包成 action
- 對應 [knowledge cards reusable-action](/backend/knowledge-cards/) (對應 DRY)

## 進階主題（按需閱讀）

### Self-hosted runner

子議題：

- 內網資源 / 特殊硬體（GPU）/ macOS
- Runner group + scaling
- Security：ephemeral runner（每次新建）
- 對應 [07 security](/backend/07-security-data-protection/)

### OIDC + cloud auth

子議題：

- GitHub OIDC provider
- AWS / GCP / Azure 信任 GitHub
- 無 long-lived access key
- 對應 supply chain security

### Environment protection

子議題：

- environment（dev / staging / prod）
- Required reviewers
- Wait timer
- Secrets per-environment
- 對應 [6.8 Release Gate](/backend/06-reliability/release-gate/)

### Workflow security

子議題：

- pull_request vs pull_request_target（後者有 secrets / 危險）
- third-party action pinning（commit SHA）
- GITHUB_TOKEN permissions（最小化）

### Deploy workflow

子議題：

- Deploy on tag / release
- Rolling deploy / blue-green / canary
- Rollback action

## 排錯快速判讀

### Workflow 沒觸發

操作原則：on trigger 配置 / branch filter / paths filter。判讀：Actions tab 看 trigger event。

### Permission denied

操作原則：GITHUB_TOKEN permissions 不夠。判讀：workflow 加 permissions: 區段。

### Cache miss

操作原則：cache key 不穩定 / hashFiles input 變化。

### Secret 沒生效

操作原則：secret name / environment 不對 / pull_request from fork 不能用 secret。

### Self-hosted runner 卡住

操作原則：runner offline / job queue 滿 / runner group 配置不對。

## 何時改走其他服務

| 需求形狀                 | 改走                                                  |
| ------------------------ | ----------------------------------------------------- |
| 進階 cache / parallelism | [CircleCI](/backend/06-reliability/vendors/circleci/) |
| 非 GitHub-hosted         | GitLab CI / Bitbucket Pipelines / CircleCI            |
| Self-hosted enterprise   | Jenkins / Buildkite / Tekton                          |
| 複雜 pipeline DAG        | Tekton / Argo Workflows                               |
| Bazel-native CI          | BuildBuddy / EngFlow                                  |

## 不在本頁內的主題

- 各 Marketplace action 細節
- GitHub Enterprise self-host
- Actions pricing
- 各語言 setup-* action 細節

## 案例回寫

**待補 GitHub Actions customer case**：大規模 monorepo Actions 採用、OIDC migration、self-hosted runner scaling 案例。

## 下一步路由

- 上游概念：[6.8 Release Gate](/backend/06-reliability/release-gate/)
- 平行 vendor：[CircleCI](/backend/06-reliability/vendors/circleci/)
- 下游能力：[07 security](/backend/07-security-data-protection/)（supply chain）、[5 deployment](/backend/05-deployment-platform/)（deploy gate）
