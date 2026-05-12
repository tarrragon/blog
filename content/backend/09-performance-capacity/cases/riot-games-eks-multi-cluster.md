---
title: "9.C12 Riot Games：246 個 EKS cluster 的多遊戲多地區治理"
date: 2026-05-12
description: "Riot Games 從 Mesos 遷移到 EKS、用 246 個 cluster 跨遊戲跨地區治理、年省 1000 萬美金"
weight: 12
tags: ["backend", "performance", "capacity", "case-study", "compute", "aws", "low-latency-sustained"]
---

這個案例的核心責任是說明「K8s 多 cluster 治理」對容量規劃的影響。Riot Games 經營 League of Legends、VALORANT、TFT 等多款全球遊戲、單一遊戲跨多地區、需要 < 35ms 延遲、需要做到「快速部署新遊戲 / 新區域」— 這套需求把容量規劃的單位從「instance」改成「cluster」。

## 觀察

Riot Games 遷移到 EKS 的關鍵數字（引自 [Riot Games case study](https://aws.amazon.com/solutions/case-studies/riot-games-case-study/)）：

| 指標                   | 數字                        |
| ---------------------- | --------------------------- |
| 月活用戶               | 1.8 億 +                    |
| Cluster 數量           | 246 個                      |
| 基礎設施年省           | 1000 萬美金                 |
| 部署速度提升           | 12x                         |
| 基礎設施設定速度       | +90%                        |
| 延遲門檻               | 35ms（VALORANT 等競技遊戲） |
| 標準化覆蓋率           | 80% 基礎設施移到中央管理    |
| 開發者基礎設施工作下降 | -40%                        |
| 事件回應時間下降       | -50%                        |

服務組合：Amazon EKS（主要）、AWS Local Zones（低延遲就近部署）、AWS Outposts（on-prem edge）、Karpenter（node lifecycle）、Terraform（IaC）。

關鍵架構決策：從 multi-tenant cluster 模型改成 *single-tenant per game* — 每個遊戲一個獨立 cluster、避免跨遊戲互相影響。

## 判讀

Riot Games 案例揭露三個多 cluster K8s 容量治理重點。

1. **Cluster 隔離是容量規劃的單位**：246 個 cluster 看似很多、但 *每個 cluster 是獨立容量單位*、不互相影響。一個遊戲的擴容不會吃掉另一個遊戲的容量。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 multi-tenant vs single-tenant 取捨。
2. **延遲門檻反推 region 部署**：35ms 是競技遊戲（VALORANT、League）的可接受上限、超過會「卡」。從這個門檻反推：玩家所在 region 不能跨洲、需要區域 cluster。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 latency budget。Local Zones / Outposts 是這個門檻的工程回應。
3. **Karpenter + Terraform = cluster 容量自動化**：246 個 cluster 手動管理會崩。Karpenter（node 動態 lifecycle）+ Terraform（IaC）讓 cluster 級操作可重複、可審查。對應 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/) 的自動化迴圈。

需要警惕：「年省 1000 萬」是 *vs 自管 Mesos*、不是 *vs 沒上雲*。EKS 仍有 vendor cost、只是比自管便宜。讀案例時要看 baseline 是什麼。另外、單一 cluster 的容量上限（pod 數、node 數）仍是工程現實、超過時要做 cluster sharding（這正是 Riot 走 246 個 cluster 的部分原因）。

## 策略

可重用的工程做法：

1. **single-tenant cluster per workload**：每個高敏感度工作負載（每個遊戲、每個關鍵服務）一個獨立 cluster、避免 noisy neighbor。對應 [05 部署平台模組](/backend/05-deployment-platform/)。
2. **延遲門檻反推 region 部署數量**：先訂 latency budget、再算 *玩家分布 × region cluster 數量*。region 增加會線性增加 ops 成本、要在 latency 跟 cost 之間找平衡。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。
3. **cluster 級 IaC + 自動化是 multi-cluster 治理前置**：Terraform / Pulumi / Crossplane + Karpenter / Cluster Autoscaler 是基本工具。

跨平台等效：GCP GKE Fleet management（multi-cluster）、Azure Fleet Manager、自建 Cluster API + ArgoCD 都可以做 multi-cluster 治理。差異是 vendor 整合度跟政策。

## 下一步路由

- 想設計 multi-cluster K8s → [05 部署平台模組](/backend/05-deployment-platform/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想做延遲門檻反推部署 → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) + [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)
- 想對照微服務 vs multi-cluster → [9.C7 Lyft](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)

## 引用源

- [Riot Games Cuts $10M Annual Infrastructure Costs by Migrating to Amazon EKS](https://aws.amazon.com/solutions/case-studies/riot-games-case-study/)
- [Riot Games on Using AWS to Improve Gaming](https://aws.amazon.com/solutions/case-studies/riot-games-reinvent/)
