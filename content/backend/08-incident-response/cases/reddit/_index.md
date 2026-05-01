---
title: "Reddit"
date: 2026-05-01
description: "Reddit Pi Day 2023 k8s 升級事故"
weight: 22
---

Reddit 2023 Pi Day（3/14）的 314 分鐘事故是 Kubernetes 升級導致的事故、揭露 k8s 升級在大規模生產環境的隱性風險。Reddit engineering blog 公開 post-mortem 細節豐富。

## 規劃重點

- Kubernetes 升級風險：minor version 升級的 breaking change
- 升級回滾困境：為何 k8s control plane 不能直接降版
- 大規模 stateful workload 的特殊性：pod 重排對狀態服務的衝擊
- 內部 IR 流程：Reddit 的 IR commander / scribe 結構公開度

## 預計收錄事故

| 年份    | 事故                     | 教學重點                            |
| ------- | ------------------------ | ----------------------------------- |
| 2023-03 | Pi Day k8s 升級 314 分鐘 | k8s upgrade、control plane 回滾困境 |

## 引用源

待補（Reddit engineering blog post-mortem URL）。
