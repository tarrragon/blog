---
title: "模組六：高可用與災難復原"
date: 2026-06-20
description: "一個節點掛了服務怎麼不中斷 — 冗餘設計、failover 機制、disaster recovery 策略"
weight: 6
tags: ["devops", "high-availability", "failover", "disaster-recovery", "redundancy"]
---

一個節點掛了，服務怎麼不跟著中斷？高可用的答案是冗餘——每個單點故障都有替代路徑。這個模組是「規模成長」路線的第三站，也建立在模組四服務探活之上：failover 的觸發條件正是探活。

## 章節

| 章節                                                                          | 回答什麼問題                                             |
| ----------------------------------------------------------------------------- | -------------------------------------------------------- |
| [單點故障盤點](/operations/06-high-availability/spof-inventory/)              | pre-mortem 反推、依賴 budget、按 blast radius 排序       |
| [冗餘設計模式](/operations/06-high-availability/redundancy-patterns/)         | active-passive / active-active / multi-region、冗餘≠備份 |
| [Failover 機制](/operations/06-high-availability/failover-mechanism/)         | 探活觸發、故障域、恢復順序的循環等待、rollback           |
| [Disaster recovery 策略](/operations/06-high-availability/disaster-recovery/) | RTO/RPO、restore drill、恢復不是切回流量就結束           |
| [高可用的成本](/operations/06-high-availability/ha-cost/)                     | 冗餘 2x、用停機代價衡量、可用性等級階梯                  |

## 跨分類引用

- → [backend 可靠性](/backend/06-reliability/)：Backend 的可靠性設計
- → [運維 模組四 服務探活](/operations/04-service-health/)：探活是 failover 的觸發條件
- → [Infra 核心服務上 IaC — Stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)：multi-AZ 是 infra 層的可用區冗餘能力，本模組的 HA 策略（健康檢查、自動恢復、failover 機制）建立在這個能力之上
- → [Infra 網路地基](/infra/03-network-foundation/)：跨可用區的 subnet 與 NAT 冗餘設計是 HA 的網路前提
