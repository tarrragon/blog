---
title: "模組八：成本管理"
date: 2026-06-20
description: "雲端帳單怎麼不失控 — reserved instance、spot instance、right-sizing、成本監控告警"
weight: 8
tags: ["devops", "cost-management", "cloud-cost", "reserved-instance", "spot-instance"]
---

回答「帳單怎麼不失控」。雲端的靈活性讓資源容易加、但也容易忘記關。這個模組是「成本控制」路線的起點，往下接模組五的容量成本模型——成本管理決定資源花得值不值得，容量規劃決定要開多少。

## 章節

| 章節                                                                             | 回答什麼問題                                        |
| -------------------------------------------------------------------------------- | --------------------------------------------------- |
| [計費模式理解](/operations/08-cost-management/billing-models/)                   | 帳單維度、承諾模式、egress 這類隱藏成本             |
| [Right-sizing](/operations/08-cost-management/right-sizing/)                     | 找過度配置、downsizing 不能砍過膝點、機型世代       |
| [成本監控與告警](/operations/08-cost-management/cost-monitoring/)                | 歸因、異常告警、showback vs chargeback              |
| [開發環境成本控制](/operations/08-cost-management/dev-environment-cost/)         | 排程關機、ephemeral 環境、CI 跑 spot、per-team 上限 |
| [自架 vs 雲端的成本交叉點](/operations/08-cost-management/self-hosted-vs-cloud/) | 兩條成本曲線、部署光譜、人力與 lock-in              |

## 跨分類引用

- → [運維 模組五 容量規劃](/operations/05-capacity-planning/)：容量規劃的成本面
- → [infra 模組八 治理好習慣](/infra/08-governance-habits/)：成本歸因的 tagging 地基 — tag 在 IaC 裡強制長出來，這裡的部門歸屬與帳單拆分才有依據
- → [monitoring 模組六 商業方案](/monitoring/06-commercial-comparison/)：監控 SaaS 的帳單也是成本管理的一部分
