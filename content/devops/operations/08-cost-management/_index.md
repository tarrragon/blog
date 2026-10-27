---
title: "模組八：成本管理"
date: 2026-06-20
description: "雲端帳單怎麼不失控 — reserved instance、spot instance、right-sizing 與成本監控告警；預算門檻、配額與停損層級的推算在本模組，各家的建置篇目前只有 GCP，放在雲端業者模組"
weight: 8
tags: ["devops", "cost-management", "cloud-cost", "reserved-instance", "spot-instance"]
aliases: ["/operations/08-cost-management/"]
---

回答「帳單怎麼不失控」。雲端的靈活性讓資源容易加、但也容易忘記關。這個模組是「成本控制」路線的起點，往下接模組五的容量成本模型——成本管理決定資源花得值不值得，容量規劃決定要開多少。

## 章節

| 章節                                                                                                                                                                                               | 回答什麼問題                                                                             |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [計費模式理解](/devops/operations/08-cost-management/billing-models/)                                                                                                                              | 帳單維度、承諾模式、egress 這類隱藏成本                                                  |
| [租用雲端主機之前的費用規劃：費用訊號的延遲、停止之前的最大超支、扣款的信用卡額度、配額與預算門檻的計算，以及停損停到哪一層](/devops/operations/08-cost-management/spend-planning-before-renting/) | 費用訊號各落後多久、停止之前的最大超支、信用卡額度、配額與預算門檻怎麼算、停損停到哪一層 |
| [Right-sizing](/devops/operations/08-cost-management/right-sizing/)                                                                                                                                | 找過度配置、downsizing 不能砍過膝點、機型世代                                            |
| [成本監控與告警](/devops/operations/08-cost-management/cost-monitoring/)                                                                                                                           | 歸因、異常告警、showback vs chargeback                                                   |
| [開發環境成本控制](/devops/operations/08-cost-management/dev-environment-cost/)                                                                                                                    | 排程關機、ephemeral 環境、CI 跑 spot、per-team 上限                                      |
| [自架 vs 雲端的成本交叉點](/devops/operations/08-cost-management/self-hosted-vs-cloud/)                                                                                                            | 兩條成本曲線、部署光譜、人力與 lock-in                                                   |

## 各家業者的實作

預算警示與停損開關落到某一家雲端時的建置與驗收，放在 [雲端業者的帳號申請與主機維運](/devops/infra/cloud-providers/) 的業者子資料夾，目前有 [GCP 上的雲端費用失控防護](/devops/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)（機制與判斷）與 [GCP 預算警示與停損開關的實測紀錄](/devops/infra/cloud-providers/gcp/hands-on/budget-killswitch-walkthrough/)（建置與驗收）。用免費方案開帳號的人，決定是否在升級之前先建預算警示與停損時，依據是帳號在試用結束後是否開始計費；Oracle Cloud、Google Cloud 與 AWS 試用結束時帳號與資源的處置，見 [雲端免費額度與小型主機的收費比較](/devops/infra/cloud-providers/pricing-comparison/) 的〈試用結束後帳號與資源的處置〉。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                | 類型 | 前置條件                                        | 規模 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ----------------------------------------------- | ---- |
| 〈GCP 上的雲端費用失控防護〉〈費用失控的來源與反應時間〉裡不分業者的部分（兩類來源、不經過帳務資料的限制）搬進〈租用雲端主機之前的費用規劃〉，新篇與 cost-monitoring 改連新篇；GCP 篇隨後縮成 GCP 的實作，那一項登記在雲端業者 GCP 資料夾的 Backlog | 主章 | 無；inbound：GCP 篇〈費用失控的來源與反應時間〉 | 中   |

## 跨分類引用

- → [運維 模組五 容量規劃](/devops/operations/05-capacity-planning/)：容量規劃的成本面；預知的活動要編多少預算、給會計的費用區間怎麼從業務預估算出來，在 [預知的大流量要加多大、編多少預算](/devops/operations/05-capacity-planning/planned-peak-sizing-and-budget/)
- → [infra 模組八 治理好習慣](/devops/infra/08-governance-habits/)：成本歸因的 tagging 地基 — tag 在 IaC 裡強制長出來，這裡的部門歸屬與帳單拆分才有依據
- → [monitoring 模組六 商業方案](/devops/monitoring/06-commercial-comparison/)：監控 SaaS 的帳單也是成本管理的一部分
- → [運維 模組九 單台主機的長期維護、服務暫停與恢復上線](/devops/operations/09-host-lifecycle/)：單台主機暫停時仍在計費的資源（磁碟、保留的 IP、備份、網路元件）與在作業系統裡關機不停止計費的情形；本模組處理帳單層的監控
