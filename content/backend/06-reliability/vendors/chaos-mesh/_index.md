---
title: "Chaos Mesh"
date: 2026-05-01
description: "Kubernetes-native chaos engineering（CNCF incubating）"
weight: 7
---

Chaos Mesh 是 PingCAP 開源、CNCF incubating 的 Kubernetes-native chaos engineering 平台、CRD-driven、覆蓋 pod / network / IO / time / kernel / DNS / stress 等故障類型。適合 k8s 為主的 chaos 設計。

## 適用場景

- Kubernetes 原生 chaos
- CRD-driven 配置（GitOps）
- 多種故障類型（network / IO / time / kernel）
- Chaos Dashboard 視覺化

## 不適用場景

- 非 k8s 環境
- 需要應用層 attack（pod-level chaos 為主）
- 商業支援需求（OSS 為主）

## 跟其他 vendor 的取捨

- vs `litmuschaos`：類似 k8s-native 定位、社群與生態差別
- vs `gremlin`：Chaos Mesh OSS / k8s-only；Gremlin 商業 / 多平台
- vs `toxiproxy`：不同層 — Toxiproxy 是 TCP proxy；Chaos Mesh k8s 控制層

## 預計實作話題

- CRD 設計（PodChaos / NetworkChaos / IOChaos）
- Chaos workflow（多步驟編排）
- Chaos Dashboard
- Schedule 與 GitOps 整合
- Steady state 驗證
