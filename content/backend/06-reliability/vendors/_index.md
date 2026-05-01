---
title: "可靠性 Vendor 清單"
date: 2026-05-01
description: "後端可靠性實作時的常用工具選擇，預先建立引用路徑"
weight: 91
---

本清單列出 backend 可靠性實作會選用的 vendor / platform：CI、load test、chaos engineering、SLO 工具。每個 vendor 一個資料夾，先建定位與取捨骨架。

跟 [cases/](/backend/06-reliability/cases/) 是不同維度 — cases 是教學案例來源（Google SRE、Netflix Chaos 等），vendors 是實作工具。

## T1 vendor

CI / 變更節奏：

- [github-actions](/backend/06-reliability/vendors/github-actions/) — CI/CD 主流
- [circleci](/backend/06-reliability/vendors/circleci/) — CI/CD 替代

Load test：

- [k6](/backend/06-reliability/vendors/k6/) — 現代 load test、Grafana Labs
- [gatling](/backend/06-reliability/vendors/gatling/) — JVM-based load test
- [jmeter](/backend/06-reliability/vendors/jmeter/) — 老牌 load test
- [locust](/backend/06-reliability/vendors/locust/) — Python-based load test

Chaos engineering：

- [chaos-mesh](/backend/06-reliability/vendors/chaos-mesh/) — Kubernetes-native chaos（CNCF）
- [litmuschaos](/backend/06-reliability/vendors/litmuschaos/) — k8s chaos（CNCF）
- [gremlin](/backend/06-reliability/vendors/gremlin/) — 商業 chaos engineering 平台
- [toxiproxy](/backend/06-reliability/vendors/toxiproxy/) — TCP-level fault injection

SLO：

- [nobl9](/backend/06-reliability/vendors/nobl9/) — SLO 平台
- [sloth](/backend/06-reliability/vendors/sloth/) — OSS SLO generator

## 後續擴充

- T2 候選：jenkins、buildkite、tekton、fuzzbench、pyrra、openslo
- T3 候選：harness、azure-pipelines、artillery、k6-cloud、steampipe
