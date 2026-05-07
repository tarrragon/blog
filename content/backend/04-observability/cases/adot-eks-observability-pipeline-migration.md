---
title: "4.C6 AWS：ADOT on EKS 管線遷移"
date: 2026-05-07
description: "從分散式 agent 組合轉成 OpenTelemetry collector 管線治理。"
weight: 6
---

這個案例的核心責任是把 observability 遷移做成管線治理，而不是單點 agent 替換。

## 觀察

AWS ADOT on EKS 的實務把 metrics、traces 採集策略整合到可管理的 collector pipeline。

## 判讀

多代理混用雖然能運作，但在規模化時會放大配置漂移與維運成本。

## 策略

1. 先統一 collector 部署模式。
2. 將 exporter 與 sampling 規則集中管理。
3. 以資料品質指標驗證遷移成效。

## 下一步路由

回 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 與 [4.18 observability operating model](/backend/04-observability/observability-operating-model/)。

## 引用源

- [AWS Distro for OpenTelemetry on EKS](https://aws-otel.github.io/docs/getting-started/adot-eks-add-on/)
