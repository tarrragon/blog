---
title: "LitmusChaos"
date: 2026-05-01
description: "Kubernetes chaos engineering 平台（CNCF graduated）"
weight: 8
---

LitmusChaos 是 CNCF graduated 的 chaos engineering 平台、ChaosHub 提供現成 experiment、Litmus Workflow 編排多步驟 chaos、SaaS 版本（Harness ChaosNative）。

## 適用場景

- Kubernetes chaos 與 GitOps
- 利用 ChaosHub 現成 experiment
- 跨集群 chaos workflow
- 商業支援（Harness）

## 不適用場景

- 非 k8s 環境
- 想要極輕量 single-purpose 工具

## 跟其他 vendor 的取捨

- vs `chaos-mesh`：類似 k8s-native；社群、UI、experiment 設計差異
- vs `gremlin`：Litmus OSS；Gremlin 商業

## 預計實作話題

- ChaosExperiment / ChaosEngine / ChaosResult CRD
- ChaosHub experiment 引用
- Litmus Workflow（多步驟）
- Harness ChaosNative 商業選項
- Probe（steady state validation）
