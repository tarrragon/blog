---
title: "運行期維運 — 服務在 production 怎麼活下來"
date: 2026-06-20
description: "負載平衡、水平擴展、流量管控、服務探活、容量規劃、高可用、突發流量、成本管理 — 服務上線後運行期的工程基礎"
weight: 38
tags: ["operations", "devops"]
---

服務寫完部署上線只是起點。上線後的日常是「流量進來了怎麼分散、服務掛了怎麼恢復、突然爆量怎麼應對、帳單怎麼不失控」。這些問題的解法在部署拓撲、流量路由、健康偵測和容量規劃的設計中。這一段是[軟體交付生命週期](/devops/)的最後一階——地基（Infra）鋪好、管線（CI/CD）把變更交付上線之後，服務怎麼在運行期穩定活著。

## 和其他系列的關係

| 系列                       | 聚焦                                           | 和運行期維運的交集                                                         |
| -------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------- |
| [DevOps 全景](/devops/)    | 交付生命週期的三階段導覽（地基 → 管線 → 維運） | 本系列是這條生命週期的運行期階段                                           |
| [Backend](/backend/)       | 服務內部的設計（資料庫、快取、佇列、可觀測性） | Backend 的部署和可靠性維度在這裡展開                                       |
| [Infra](/infra/)           | 基礎設施地基（IaC、網路、身分、環境分離）      | 運維管的服務跑在 Infra 鋪好的地基上                                        |
| [Monitoring](/monitoring/) | 客戶端監控體系（SDK、Collector、Dashboard）    | Collector 的 ingestion scaling 是這裡的流量管控應用                        |
| [CI/CD](/ci/)              | 驗證、建置、發布 gate                          | CI/CD 管線的產出（artifact）是這裡部署的輸入                               |
| [Testing](/testing/)       | 測試策略與 mock 邊界                           | 服務 fixture 的 health check 和服務探活概念共通                            |
| [UX Design](/ux-design/)   | 畫面設計與 gate fallback                       | Server 端限速（429）影響 client 端的重試 UX 和離線 UX                      |
| [Dotfile](/linux/dotfile/) | 個人工作環境配置管理                           | 維運工程師的日常工具鏈（多終端機、SSH、log tail）是 dotfile 高度客製的場景 |

Backend 教「服務怎麼設計」，運行期維運教「設計好的服務怎麼在 production 活下來」。

## 教學模組

| 模組                                                   | 主題                                         | 回答什麼問題                          |
| ------------------------------------------------------ | -------------------------------------------- | ------------------------------------- |
| [模組一：負載平衡](/operations/01-load-balancing/)     | 反向代理、負載分散、健康檢查路由             | 流量進來怎麼分給多個服務實例          |
| [模組二：水平擴展](/operations/02-horizontal-scaling/) | Stateless 設計、shared storage、session 處理 | 一個實例不夠時怎麼加第二個            |
| [模組三：流量管控](/operations/03-traffic-management/) | 背壓、rate limit、熔斷、bulkhead             | 收到的流量超過處理能力時怎麼辦        |
| [模組四：服務探活](/operations/04-service-health/)     | 探活、liveness/readiness、自動重啟           | 服務掛了怎麼自動發現和恢復            |
| [模組五：容量規劃](/operations/05-capacity-planning/)  | 壓力測試、峰值估算、成本模型                 | 要準備多少資源才夠                    |
| [模組六：高可用](/operations/06-high-availability/)    | 冗餘、failover、disaster recovery            | 一個節點掛了服務怎麼不中斷            |
| [模組七：突發流量](/operations/07-burst-traffic/)      | 突發流量應對、降級策略、queue 緩衝           | 行銷活動或新聞曝光帶來 10x 流量怎麼撐 |
| [模組八：成本管理](/operations/08-cost-management/)    | 雲端成本、reserved instance、spot instance   | 帳單怎麼不失控                        |

## 學習路線

| 路線       | 適合讀者                       | 建議順序                                                                                                                                 |
| ---------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 單服務營運 | 第一次部署 production 的開發者 | [模組四](/operations/04-service-health/) → [模組三](/operations/03-traffic-management/) → [模組一](/operations/01-load-balancing/)       |
| 規模成長   | 服務開始遇到效能瓶頸           | [模組五](/operations/05-capacity-planning/) → [模組二](/operations/02-horizontal-scaling/) → [模組六](/operations/06-high-availability/) |
| 突發應對   | 準備行銷活動或預期高峰         | [模組七](/operations/07-burst-traffic/) → [模組三](/operations/03-traffic-management/) → [模組五](/operations/05-capacity-planning/)     |
| 成本控制   | 雲端帳單開始顯著成長           | [模組八](/operations/08-cost-management/) → [模組五](/operations/05-capacity-planning/)                                                  |

上面四條路線是「從零建構」的視角。實務上還有兩個高頻情境不是從零開始，入口不同：

- **接手別人的環境、要先搞懂現況**：先盤點單點與依賴（[模組六：單點故障盤點](/operations/06-high-availability/spof-inventory/) 的 pre-mortem 反推現有部署哪裡會壞）、再從真實流量抽出模型看它現在承受什麼（[模組五：流量模型建立](/operations/05-capacity-planning/traffic-model/)）、以及盤點花在哪（[模組八：成本監控與告警](/operations/08-cost-management/cost-monitoring/) 的歸因）。這三篇合起來是「盤點既有」的入口。
- **半夜被叫起來救火、事後要正規化**：事故當下依類型分流——過載進 [模組三 流量管控](/operations/03-traffic-management/)、服務死活進 [模組四 服務探活](/operations/04-service-health/)、節點掛了進 [模組六 高可用](/operations/06-high-availability/)；事後正規化把臨時救火變成常態防線，回 [模組四](/operations/04-service-health/)（把探活與自動告警建起來）與 [模組六：Disaster recovery 策略](/operations/06-high-availability/disaster-recovery/)（把「有計畫沒演練」的 DR 補上演練）。
