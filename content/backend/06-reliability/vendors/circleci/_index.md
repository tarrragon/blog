---
title: "CircleCI"
date: 2026-05-01
description: "CI/CD 平台、強 cache 與 parallelism"
weight: 2
---

CircleCI 是獨立 CI/CD 平台、強項是 caching、parallelism、resource class 彈性。在 GitHub Actions 普及前是主流選擇之一。

## 適用場景

- 需要進階 cache / parallelism
- 跨 VCS（GitHub / Bitbucket / GitLab）
- 既有 CircleCI 投資的團隊
- 需要 macOS runner

## 不適用場景

- GitHub-only 且不需進階特性（用 GitHub Actions）
- 預算敏感（pricing 較貴）

## 跟其他 vendor 的取捨

- vs `github-actions`：見 GitHub Actions 篇
- vs Jenkins：CircleCI managed
- vs Buildkite：類似定位、Buildkite agent-first

## 預計實作話題

- Workflow / job / orb 模型
- Cache 與 workspace
- Parallelism / test splitting
- Resource class 與成本
- Self-hosted runner
- OIDC integration
