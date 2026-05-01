---
title: "Gremlin"
date: 2026-05-01
description: "商業 chaos engineering 平台、跨平台與 GameDay"
weight: 9
---

Gremlin 是商業 chaos engineering SaaS、跨平台（VM / container / k8s / cloud）、GameDay 設計與報告功能、企業偏好的選擇。Founder 來自 Netflix Chaos team。

## 適用場景

- 跨平台 chaos（不只 k8s）
- 商業支援與 SLA 需求
- GameDay 設計、團隊演練
- 不想自管 OSS chaos 工具

## 不適用場景

- OSS 偏好 / 預算敏感
- 純 k8s 環境想用 OSS（用 Chaos Mesh / Litmus）

## 跟其他 vendor 的取捨

- vs `chaos-mesh` / `litmuschaos`：Gremlin 商業 / 跨平台
- vs AWS Fault Injection Service：Gremlin 跨雲；FIS AWS-only

## 預計實作話題

- Attack types（resource / state / network）
- Blast radius 與 magnitude
- Scenario / GameDay 設計
- Halt button（緊急中止）
- 跨平台 agent 部署
