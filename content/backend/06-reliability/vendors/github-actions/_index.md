---
title: "GitHub Actions"
date: 2026-05-01
description: "GitHub 原生 CI/CD、PR check、deploy gate"
weight: 1
---

GitHub Actions 是 GitHub 原生的 CI/CD 工具、跟 PR / Issue / Release 深度整合、marketplace action 生態廣。是 GitHub-hosted 專案的預設 CI 選擇。

## 適用場景

- GitHub-hosted 專案的 PR check
- 一般 build / test / lint workflow
- Release 自動化
- 跨 platform matrix testing
- Self-hosted runner 滿足內網需求

## 不適用場景

- 不在 GitHub 的專案
- 需要極端複雜 pipeline DAG
- Build cache / artifact 體驗不夠（vs Bazel-native CI）

## 跟其他 vendor 的取捨

- vs `circleci`：GitHub Actions 整合度高；CircleCI 在 cache / parallelism 較強
- vs Jenkins：GitHub Actions managed；Jenkins 自管彈性
- vs Buildkite：Buildkite agent-first 模型、企業偏好

## 預計實作話題

- Workflow 設計（job / step / matrix）
- Cache 策略（actions/cache）
- Reusable workflows / composite actions
- Self-hosted runner
- Deploy gate / environment protection rules
- OIDC + cloud auth（無 long-lived secret）
