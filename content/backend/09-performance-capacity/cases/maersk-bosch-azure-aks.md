---
title: "9.C33 Maersk + Bosch：傳統產業在 Azure AKS 上的微服務治理"
date: 2026-05-13
description: "全球海運 Maersk 跟 Bosch 智慧建築把 AKS 當微服務治理基礎、釋放工程資源做業務功能"
weight: 33
tags: ["backend", "performance", "capacity", "case-study", "compute", "azure", "sustained-growth"]
---

這個案例的核心責任是補強 Azure compute / K8s 維度缺口。Maersk（全球最大貨櫃航運公司、每天處理百萬級貨櫃移動）跟 Bosch（德國工業集團、智慧建築 IoT）是 *傳統產業上雲* 的代表 — 跟 [9.C12 Riot Games 雲原生 EKS](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 形成對比、傳統產業的 K8s 採用動機跟雲原生公司不同。

## 觀察

Maersk + Bosch 在 Azure AKS 的關鍵敘述（引自 [AKS Customer Stories](https://azure.microsoft.com/en-us/products/kubernetes-service/)）：

| 維度          | Maersk                                                  | Bosch Software Innovations                                            |
| ------------- | ------------------------------------------------------- | --------------------------------------------------------------------- |
| 行業          | 全球海運                                                | 工業 IoT（Connected Building Solution）                               |
| 主要 workload | 貨櫃追蹤、港口物流、行程規劃                            | 樓宇感測、能源管理、設備運維                                          |
| AKS 用途      | deployment + 運維 + 管理 Kubernetes API                 | microservices 監控、不同 release cycle                                |
| 工程訴求      | 「focus on things that makes the most business impact」 | 「simplify management of microservices released on different cycles」 |
| 服務組合      | AKS + Azure 管理工具                                    | AKS + monitoring capabilities                                         |

其他常見 AKS 大客戶：Siemens Healthineers（醫療設備）、Finastra（金融軟體）、Hafslund（能源）。

## 判讀

Maersk 跟 Bosch 案例揭露三個傳統產業 K8s 治理的工程重點。

1. **傳統產業上 K8s 的動機是「治理一致性」、不是「成長彈性」**：
   - 雲原生公司（Riot、Netflix）上 K8s 是為了 *快速擴容* 跟 *跨 region 部署*
   - 傳統產業上 K8s 是為了 *統一 50+ 個應用團隊的部署流程*、降低 ops 複雜度
   - 訴求不同、配置不同 — 傳統產業可能用 *較大 node、較少 cluster*、不是 [9.C12 Riot 246 cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 那種多 cluster 策略
2. **微服務 release cycle 多元化是傳統產業上 K8s 的核心需求**：Bosch Connected Building 有「樓宇感測 daily release、能源計費 weekly release、設備運維 monthly release」、每個 release cycle 不同。K8s + GitOps（Argo CD、Flux）讓不同 cycle 共存於同一 cluster。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 release governance。
3. **「focus on business impact」是 managed K8s 的真正價值**：Maersk 不是科技公司、是航運公司。工程資源從 *維持 K8s 運維* 釋放到 *貨櫃追蹤演算法、港口物流優化*、是商業 ROI 的關鍵。對應 [9.C29 Lemino 90% 工程工時下降](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 的同類訴求、跟 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/) 的人力成本工程化。

需要警惕：Azure 官方對 Maersk / Bosch 的描述偏行銷、缺具體 throughput / latency 數字。讀此類案例要對 *策略* 學習、不要套用數字。

## 策略

可重用的工程做法：

1. **傳統產業 K8s 採用先做「單一 cluster 多 namespace」、再考慮多 cluster**：管理 1 個大 cluster 比管理 246 個小 cluster 容易。除非有 [9.C12 Riot Games 的隔離需求](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)、否則 single-cluster-multi-namespace 是 sane default。
2. **不同 release cycle 用 GitOps + namespace 隔離**：每個團隊 own 自己的 namespace、配合 Argo CD / Flux 各自 release。對應 [05 部署平台模組](/backend/05-deployment-platform/)。
3. **AKS / EKS / GKE 的差異對傳統產業不關鍵**：選哪家通常取決於企業已用哪家 cloud、不是 K8s feature 本身。重點是 *managed K8s ops 比自管划算*、不是哪家 managed 最好。
4. **監控訊號設計按業務 cycle**：每天 release 的服務跟每月 release 的服務 monitoring 策略不同、alert 敏感度不同。對應 [04 可觀測性模組](/backend/04-observability/)。

跨平台等效：AWS EKS、GCP GKE、自管 Kubernetes + Rancher 都可實作對等架構。Azure 在 enterprise 整合（Active Directory、Azure DevOps）有優勢、特別適合 Microsoft 生態企業。

## 下一步路由

- 對照雲原生 K8s 策略 → [9.C12 Riot Games 246 cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)
- 對照其他 managed 服務釋放工程資源 → [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) / [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)
- 想設計 K8s 治理 → [05 部署平台模組](/backend/05-deployment-platform/) + [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)

## 引用源

- [Azure Kubernetes Service customer stories](https://azure.microsoft.com/en-us/products/kubernetes-service/)
- [Maersk Azure case](https://customers.microsoft.com/en-us/story/maersk-travel-transportation-azure)
- [Bosch Software Innovations](https://azure.microsoft.com/en-us/blog/product/azure-kubernetes-service-aks/)
- [Kubernetes on Azure - Enterprise Expertise](https://azure.microsoft.com/en-us/solutions/kubernetes-on-azure)
