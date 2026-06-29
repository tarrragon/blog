---
title: "9.C8 Niantic Pokémon GO：在 GCP 上承載 50 倍突發流量"
date: 2026-05-12
description: "Pokémon GO 上線時實際流量達原始預估 50 倍、Google CRE 怎麼即時補容量"
weight: 8
tags: ["backend", "performance", "capacity", "case-study", "compute", "gcp", "surge"]
---

這個案例的核心責任是說明「surge load」（突發遠超預期）跟 event-peak（事件型可預測峰值）的差異。Pokémon GO 在 2016-07 上線時、實際流量達到原始容量規劃目標的 50 倍 — 根因是 *根本沒人能預測這個產品會這麼紅*、峰值規劃方法論本身沒有失敗。這類負載對容量設計的要求跟其他案例本質不同。

## 觀察

Niantic Pokémon GO 在 GCP 上的關鍵敘述（引自 [Bringing Pokémon GO to life on Google Cloud](https://cloud.google.com/blog/products/gcp/bringing-pokemon-go-to-life-on-google-cloud)）：

| 指標     | 數字                               |
| -------- | ---------------------------------- |
| 實際流量 | 達到原始 target 的 50 倍           |
| 應用層   | Google Container Engine (GKE)      |
| 容器編排 | Kubernetes（planetary-scale 設計） |
| 容量支援 | Google CRE 即時擴容                |

關鍵敘述：「Niantic chose GKE for its ability to orchestrate container clusters at planetary-scale」「Google CRE seamlessly provisioned extra capacity on behalf of Niantic to stay ahead of their record-setting growth」。

## 判讀

這個案例最重要的判讀是「surge load 跟可預測峰值是不同問題」。

1. **50x surge 沒辦法事前規劃**：任何合理的 capacity planning 都不會預留 50x headroom — 那會讓平日成本爆炸。surge 的工程做法不是「事前撐住」、是「事中快速補上」。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 跟 [08 事故處理模組](/backend/08-incident-response/) 的事件管理。
2. **CRE 不是技術、是 vendor 關係**：Google Customer Reliability Engineering 是 GCP 提供給戰略客戶的 24/7 工程支援團隊。能即時為 Niantic 補容量靠的是 *人 + 流程 + 工具* 的組合、不是純技術。對應 [00.6 操作控制服務選型](/backend/00-service-selection/operations-control-service-selection/) 的廠商支援能力評估。
3. **Kubernetes 是 surge 的前置條件**：如果 Niantic 用 VM-based 架構、即使 CRE 想補容量也來不及 boot up。Container orchestrator 把 provisioning 時間從分鐘級降到秒級、才讓 surge 反應變得可能。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 platform 選型。

需要警惕：「Google CRE 即時補容量」這種敘述對中小客戶不適用。一般客戶在 surge 下能依賴的是 *自己的 autoscaler*、不是 vendor 工程師。設計 surge 對應策略時要假設「沒有 vendor 救援」。

## 策略

可重用的工程做法：

1. **接受 surge 不可避免、設計快速 onboard 流程**：核心問題不是「會不會 surge」、是「surge 之後 24 小時內能不能撐住」。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 跟 [08.8 incident communication](/backend/08-incident-response/incident-communication/)。
2. **降級機制作為 surge 救命稻草**：當容量不足時、優先保住核心功能、暫時關閉非核心。對應 [02.3 cache stampede](/backend/02-cache-redis/) 跟 [01.6 high concurrency access](/backend/01-database/high-concurrency-access/) 的降級設計。
3. **預先談好 vendor 緊急支援條款**：戰略服務在簽約時就要談好 surge 期間的容量配額、限流豁免、CRE / TAM 支援、不要等出事才談。對應 [00 服務選型模組](/backend/00-service-selection/) 的 vendor relationship 設計。
4. **container-first 是 surge 反應的前置**：VM-based 架構在 surge 下擴容速度比 container 慢一個量級、會直接成為 bottleneck。

跨平台等效：AWS Enterprise Support + TAM、Azure Premier Support + CSAM 都有對等服務、但能即時動用工程師補容量的程度跟客戶等級綁定。

## 下一步路由

- 想對應 surge load → [9.11 高峰事件準備](/backend/09-performance-capacity/) + [08.6 incident severity trigger](/backend/08-incident-response/incident-severity-trigger/)
- 想設計降級策略 → [01.6 high concurrency access](/backend/01-database/high-concurrency-access/) + [02 快取模組](/backend/02-cache-redis/)
- 想評估 vendor 支援 → [00.6 operations control service selection](/backend/00-service-selection/operations-control-service-selection/)
- 對照可預測峰值案例 → [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)

## 引用源

- [Bringing Pokémon GO to life on Google Cloud](https://cloud.google.com/blog/products/gcp/bringing-pokemon-go-to-life-on-google-cloud)
- [Google Customer Reliability Engineering](https://cloud.google.com/customer-reliability-engineering)
