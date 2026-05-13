---
title: "9.C34 GCP：130,000-node GKE cluster 的工程極限"
date: 2026-05-13
description: "Google 用單一 GKE control plane 跑 13 萬個 node、AI workload + 1000 Pods/sec 創建吞吐"
weight: 34
tags: ["backend", "performance", "capacity", "case-study", "compute", "gcp", "low-latency-sustained"]
---

這個案例的核心責任是揭示「現代 AI workload 對 Kubernetes 規模極限的拉扯」。跟 [9.C12 Riot Games 246 cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 走「多小 cluster 隔離」相反 — GCP 內部驗證的是「單一巨大 cluster 集中管理」、為前沿 LLM 訓練的萬卡叢集需求設計。

## 觀察

GCP 130K-node GKE cluster 實驗（引自 [How we built a 130,000-node GKE cluster](https://cloud.google.com/blog/products/containers-kubernetes/how-we-built-a-130000-node-gke-cluster)）：

| 指標                   | 數字                              |
| ---------------------- | --------------------------------- |
| 實驗節點數             | 130,000（vs 官方支援 65,000）     |
| Pod 創建峰值           | 1,000 Pods / 秒                   |
| Phase 1 deploy 時間    | 130,000 Pods in 3 分 40 秒        |
| Phase 2 batch 創建     | 65,000 Pods in 81 秒              |
| Preemption 峰值        | 39,000 Pods preempted in 93 秒    |
| Pod startup p99        | ~10 秒（inference workload）      |
| API server LIST p99    | 「well below defined thresholds」 |
| Database objects       | 100 萬 +                          |
| Lease 更新 QPS         | 13,000                            |
| 客戶當前範圍           | 20-65K node range                 |
| 預期 cluster size 穩定 | 100K node mark                    |

工作負載類型：AI / ML 平台、三個 priority class：

- Low：preemptible batch（data prep）
- Medium：core model training（tolerant to queuing）
- High：latency-sensitive inference

關鍵 control plane 設計：

- Consistent Reads from Cache（KEP-2340）— 強一致 read 從 in-memory cache、不打 storage
- Snapshottable API Server Cache（KEP-4988）— B-tree snapshot 處理 LIST 請求
- Spanner-based key-value store 作為 K8s storage backend（撐 13K QPS lease 更新）

## 判讀

130K-node 案例揭露三個 hyperscale K8s 設計的工程重點。

1. **單一 control plane 的極限取決於 storage backend、不是 nodes**：130K node 不是「機器跑不動」、是「API server 跟 etcd 撐不撐住」。GCP 用 Spanner 替換 etcd、配上 cache-first read 設計、把 storage 從瓶頸變成「showed no signs of not being able to support higher scales」。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 的「真實 bottleneck 在哪一層」。
2. **AI workload 顛覆了 K8s 容量規劃**：傳統 web workload 的 K8s 多在 1K-10K node、節點生命週期長。AI workload 短時間爆量創建跟銷毀 Pods（13 萬個 in 3 分 40 秒）、preempt 跟 schedule 頻繁、對 control plane 是完全不同壓力模式。對應 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) — workload 形狀完全不同、容量規劃也完全不同。
3. **「power constraint > chip supply」是新瓶頸**：單顆 NVIDIA GB200 GPU 吃 2700W、萬卡叢集 = 27MW 用電量。未來 mega cluster 必須跨多個 data center（一個 DC 電力撐不住）、需要 *robust multi-cluster solutions*。這層瓶頸跟 [9.7 成本邊界](/backend/09-performance-capacity/cost-engineering/) 對接 — 電力成本變成主要 cost driver。

需要警惕：

- 130K-node 是 *Google 內部實驗*、不是 *客戶能用的 production* 配置。目前 GKE 官方支援 65K node、客戶用到 100K+ 還很遠。
- AI workload 跟 web workload 完全不同、把 AI 經驗套用到 web service 容量規劃是錯誤類比。

## 策略

可重用的工程做法：

1. **K8s control plane 跟 data plane 分開規劃容量**：data plane（worker nodes）擴容容易、control plane（API server、etcd / storage）擴容難。瓶頸通常在 control plane、不是 worker。
2. **storage backend 是 K8s 規模極限的關鍵**：etcd 撐 5K-10K node 後開始吃力、要用 PostgreSQL / Spanner / 自家 KV 替換、才能擴到萬級節點。一般客戶用不到、但要知道「為什麼到某個規模 etcd 不夠」。
3. **AI workload 用 specialized scheduler**（Kueue、Volcano）：默認 K8s scheduler 為 web workload 設計、AI 的 gang scheduling、fair-sharing、preemption 都不太適合。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 scheduler 選型。
4. **power-aware capacity planning 是未來方向**：傳統按 CPU / RAM 規劃容量、未來要加上 *power budget*。data center 用電量是硬上限、不是錢的問題。
5. **multi-cluster 是萬卡訓練的必然**：單一 cluster 撐不住、要 MultiKueue 等跨 cluster 排程方案。對應 [9.C12 Riot Games multi-cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 但目的完全不同。

跨平台等效：AWS EKS 官方支援單 cluster 多至 100K pod / cluster、Azure AKS 支援 5K node / cluster。GCP 用 Spanner 替換 etcd 是最深的工程投資、目前其他兩家還沒到這個規模。

## 下一步路由

- 對照其他大規模 K8s → [9.C12 Riot Games 246 cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)（多 cluster 策略）
- 對照 AI workload → [9.C8 Pokemon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)（非 AI 但同 GCP K8s）
- 想理解 control plane vs data plane → [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 想設計 K8s 容量上限 → [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) + [05 部署平台模組](/backend/05-deployment-platform/)

## 引用源

- [How we built a 130,000-node GKE cluster](https://cloud.google.com/blog/products/containers-kubernetes/how-we-built-a-130000-node-gke-cluster)
- [GKE and Kubernetes at KubeCon 2025](https://cloud.google.com/blog/products/containers-kubernetes/gke-and-kubernetes-at-kubecon-2025)
- [What's new in GKE at Next 26](https://cloud.google.com/blog/products/containers-kubernetes/whats-new-in-gke-at-next26)
