---
title: "CircleCI"
date: 2026-05-01
description: "CI/CD 平台、強 cache 與 parallelism"
weight: 2
tags: ["backend", "reliability", "vendor"]
---

CircleCI 是獨立 CI/CD 平台、承擔三個責任：強進階 cache（layer-aware）+ parallelism（test splitting）、跨 VCS（GitHub / Bitbucket / GitLab）、resource class 彈性（含 macOS / ARM / GPU）。設計取捨偏向「進階 cache + 並行加速 + cross-VCS」、適合需要極致 build speed 跟 macOS runner 的團隊。

## 本章目標

讀完本章後、你應該能：

1. 寫 .circleci/config.yml workflow
2. 設計 cache + workspace 加速 build
3. 用 parallelism + test splitting
4. 選 resource class（CPU / memory / macOS / GPU）
5. 評估 CircleCI vs GitHub Actions 的選用

## 最短路徑：5 分鐘把 CircleCI 跑起來

```yaml
# .circleci/config.yml
version: 2.1
jobs:
  test:
    docker: [{image: cimg/node:20}]
    steps:
      - checkout
      - run: npm test
workflows:
  ci:
    jobs: [test]
```

## 日常操作與決策形狀

### Pipeline / workflow / job 模型

子議題：

- Pipeline（一次 trigger 的執行）
- Workflow（多 job 編排、DAG）
- Job（一組 step）
- 對應指令範例：`circleci local execute`（本地測 config）

### Orb 重用

子議題：

- Orb = package of reusable config（types / commands / jobs / executors）
- Public orb registry（circleci.com/developer/orbs）
- Private orb for company

### Cache + workspace

子議題：

- Cache：跨 build 保留（dependency / build artifact）
- Workspace：同 workflow 內 job 之間傳遞
- Cache key 設計（與 GitHub Actions 類似）

## 進階主題（按需閱讀）

### Parallelism + test splitting

子議題：

- Job parallelism N
- Test splitting by timing / name / class
- 對應 test suite 加速

### Resource class

子議題：

- small / medium / large / xlarge / 2xlarge
- macOS / Arm / GPU classes
- 跟 cost 平衡

### Self-hosted runner

子議題：

- Runner agent
- 適合：內網 / 特殊環境

### OIDC integration

子議題：

- OIDC token → AWS / GCP（無 long-lived secret）
- 跟 GitHub Actions 同 pattern

### Approval job

子議題：

- type: approval job：人工介入
- 對應 [6.8 Release Gate](/backend/06-reliability/release-gate/)

### Cross-VCS support

子議題：

- GitHub / Bitbucket / GitLab
- 跟 GitHub Actions 只 GitHub 對比

## 排錯快速判讀

### Build 慢

操作原則：cache miss / test 沒 split / resource class 太小。

### Cache 不命中

操作原則：cache key 設計問題 / key change。

### Parallelism 不均勻

操作原則：test split strategy（timing 最好但要 historical data）。

### Approval 卡住

操作原則：approval job 沒人按 / on-call 不在。

## 何時改走其他服務

| 需求形狀               | 改走                                                              |
| ---------------------- | ----------------------------------------------------------------- |
| GitHub-hosted          | [GitHub Actions](/backend/06-reliability/vendors/github-actions/) |
| Self-hosted enterprise | Jenkins / Buildkite / Tekton                                      |
| GitLab-hosted          | GitLab CI                                                         |
| 複雜 DAG / K8s-native  | Tekton / Argo Workflows                                           |
| 預算敏感               | GitHub Actions / self-hosted Jenkins                              |

## 不在本頁內的主題

- 各 Orb 細節
- CircleCI Server（self-host enterprise）
- Pricing 細節

## 案例回寫

**待補 CircleCI customer case**：大規模 CircleCI 採用、macOS / iOS CI 加速案例、CircleCI → GitHub Actions 遷移案例。

## 下一步路由

- 上游概念：[6.8 Release Gate](/backend/06-reliability/release-gate/)
- 平行 vendor：[GitHub Actions](/backend/06-reliability/vendors/github-actions/)
- 下游能力：[07 security](/backend/07-security-data-protection/)、[5 deployment](/backend/05-deployment-platform/)
