---
title: "模組六：高可用與災難復原"
date: 2026-06-20
description: "一個節點掛了服務怎麼不中斷 — 冗餘設計、failover 機制、disaster recovery 策略"
weight: 6
tags: ["devops", "high-availability", "failover", "disaster-recovery", "redundancy"]
---

一個節點掛了，服務怎麼不跟著中斷？高可用的答案是冗餘——每個單點故障都有替代路徑。這個模組是「規模成長」路線的第三站，也建立在模組四服務探活之上：failover 的觸發條件正是探活。

## 章節

| 章節                                                                                      | 回答什麼問題                                                                                                                                                        |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [單點故障盤點](/operations/06-high-availability/spof-inventory/)                          | pre-mortem 反推、依賴 budget、按 blast radius 排序                                                                                                                  |
| [冗餘設計模式](/operations/06-high-availability/redundancy-patterns/)                     | active-passive / active-active / multi-region、冗餘≠備份                                                                                                            |
| [Failover 機制](/operations/06-high-availability/failover-mechanism/)                     | 探活觸發、故障域、恢復順序的循環等待、rollback                                                                                                                      |
| [Disaster recovery 策略](/operations/06-high-availability/disaster-recovery/)             | RTO/RPO、restore drill、恢復不是切回流量就結束                                                                                                                      |
| [高可用的成本](/operations/06-high-availability/ha-cost/)                                 | 冗餘 2x、用停機代價衡量、可用性等級階梯                                                                                                                             |
| [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/) | 第二台給監控、應用副本或資料庫各換到什麼，監控跨業者經 VPN 讀取，兩台互相監看，第三台給資料庫或兩台應用主機搭配託管資料庫，加主機換不到、由雲端業者或入口處理的故障 |

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 類型 | 前置條件       | 規模 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---- | -------------- | ---- |
| 〈小型服務的兩到三台主機配置〉的實機驗證：監控主機在另一個業者或地端、經 VPN 讀取、兩台互相監看與兩地連線中斷的誤判、服務主機上自架 healthchecks 的部署（`SITE_ROOT`、寄信設定、接收端只綁 VPN、監控主機以 blackbox_exporter 探測它）、VPN 裡只讓監控主機連得到 exporter 連接埠（Tailscale ACL 或 WireGuard 端的防火牆規則；只綁 VPN 位址時 VPN 裡每一台裝置都連得到）、主機開機時 Docker 早於 VPN 介面啟動、要綁的 VPN 位址還不存在時發佈的連接埠會不會失敗與處置（依機制推論、未實測）、[7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的限制實測（地端隧道介面只接受回應時雲端發起的連線被擋下、在雲端改寫 AllowedIPs 加入地端區網之後仍到不了區網、Tailscale ACL 收窄之後雲端連不到其他裝置、丟棄紀錄與 `wg show` 的握手欄位），驗完把設計段落改成實測與指令 | 主章 | 第二台主機啟動 | 中   |

## 跨分類引用

- → [backend 可靠性](/backend/06-reliability/)：Backend 的可靠性設計
- → [運維 模組四 服務探活](/operations/04-service-health/)：探活是 failover 的觸發條件
- → [Infra 核心服務上 IaC — Stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)：multi-AZ 是 infra 層的可用區冗餘能力，本模組的 HA 策略（健康檢查、自動恢復、failover 機制）建立在這個能力之上
- → [Infra 網路地基](/infra/03-network-foundation/)：跨可用區的 subnet 與 NAT 冗餘設計是 HA 的網路前提
