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

## Backlog

| 項目                                                                                                                                                                                                                                                                                                                                           | 類型 | 前置條件                                                                       | 規模       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------ | ---------- |
| GCP 帳單帳戶的支出防護實作篇：預算警示（只通知、費用資料延遲數小時）、強制執行支出上限（只涵蓋 Cloud Run、Cloud Run Functions、Gemini API、Vertex AI 這類服務，Compute Engine 與 GKE 不在內）、以預算通知經 Pub/Sub 觸發 function 自動停用帳單，以及服務出錯或遭攻擊時費用暴增、人工來不及阻止的情境；自動停用帳單要在測試專案實際觸發一次再寫 | 主章 | 有連結 blog-test 帳單帳戶的 GCP 測試專案，自動停用帳單的 function 部署並觸發過 | 1 篇（中） |

自動停用帳單是〈開發環境成本控制〉的「Per-team 成本上限」一節裡「超過就告警甚至自動限制」的實作面；兩邊的分工是那一節講為什麼要設上限，這一篇講在 GCP 上各種機制實際擋得住什麼、擋不住什麼。

## 跨分類引用

- → [運維 模組五 容量規劃](/operations/05-capacity-planning/)：容量規劃的成本面
- → [infra 模組八 治理好習慣](/infra/08-governance-habits/)：成本歸因的 tagging 地基 — tag 在 IaC 裡強制長出來，這裡的部門歸屬與帳單拆分才有依據
- → [monitoring 模組六 商業方案](/monitoring/06-commercial-comparison/)：監控 SaaS 的帳單也是成本管理的一部分
