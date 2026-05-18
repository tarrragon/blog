---
title: "CloudHealth"
date: 2026-05-15
description: "用 enterprise FinOps governance、policy 與多雲成本管理支援大型組織的容量成本治理"
weight: 22
tags: ["backend", "performance", "capacity", "vendor", "cloudhealth", "finops"]
---

CloudHealth 的核心責任是把大型組織的 cloud spend、governance、policy、allocation 與 optimization workflow 放進同一個 FinOps 管理平面。它適合 account、team、business unit、provider 與採購流程複雜的組織，重點在讓成本治理、合規要求與工程 owner 能共用同一套成本事實。

## 定位

CloudHealth 適合 enterprise FinOps 與 cloud governance。當組織需要跨 AWS、Azure、Google Cloud、Kubernetes、shared services 與成本中心建立 showback、chargeback、policy 與 optimization workflow，CloudHealth 類平台可以提供集中式成本管理與治理視角。

這個定位讓 CloudHealth 接到三個主章。它從 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/) 接收 cost curve 與 over-provision waste，從 [9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/) 接收成本 dashboard 需求，從 [04 可觀測性成本歸因](/backend/04-observability/cost-attribution/) 接收 owner、tag 與 attribution 規則。

## 適用場景

多雲成本治理是 CloudHealth 的主要入口。大型企業常有不同 cloud provider、不同採購合約、不同 account 結構與不同團隊成熟度；CloudHealth 可以把成本、資產、policy 與權限治理收斂到 FinOps 工作流程。

Showback / chargeback 適合用 CloudHealth 建立財務語言。成本中心、部門、產品線、環境與專案需要穩定分攤規則，才能讓工程決策接到預算管理、採購承諾與年度規劃。

Optimization workflow 適合用 CloudHealth 管理組織節奏。Rightsizing、reserved capacity、idle resource、tag compliance 與 policy violation 都需要 owner、例外、核准、驗證與追蹤，enterprise 平台的價值在於流程一致。

## 選型判準

| 判準            | CloudHealth 的價值                             | 需要補的能力                            |
| --------------- | ---------------------------------------------- | --------------------------------------- |
| 組織治理        | 支援多 account、多團隊、成本中心與 policy      | FinOps operating model、owner taxonomy  |
| 成本分攤        | 支援 showback / chargeback 與 shared cost rule | tag hygiene、成本中心對照表             |
| 最佳化流程      | 支援 rightsizing、commitment 與 policy action  | 工程驗證、變更排程、saving confirmation |
| Enterprise 整合 | 適合採購、財務、平台與工程共同使用             | 權限模型、報表治理、例外處理            |

組織治理價值來自一致流程。單一工程團隊可以靠雲端原生工具追成本；大型組織需要 policy、role、approval、exception 與 audit trail 才能讓成本治理長期運作。

成本分攤價值來自可對帳。Showback / chargeback 要能讓財務、平台與服務 owner 對同一筆費用得到相同解釋，shared platform cost、discount、support fee 與 commitment benefit 都要有分攤規則。

最佳化流程價值來自閉環管理。Rightsizing recommendation 只有在 owner 接手、服務驗證、變更落地與 saving confirmation 完成後，才會變成實際成本改善。

## 跟其他工具的取捨

CloudHealth 和 Vantage 的主要差異是治理深度。Vantage 偏工程友善報表與 Kubernetes cost visibility；CloudHealth 偏 enterprise FinOps operating model、policy 與大組織分攤流程。

CloudHealth 和 Akamas 的主要差異是最佳化方式。CloudHealth 偏成本治理與推薦流程；Akamas 偏把 SLO 約束與 configuration tuning 放進 optimization engine。

CloudHealth 和 AWS Cost Explorer 的主要差異是多雲與流程。Cost Explorer 適合 AWS-native 成本分析；CloudHealth 適合跨 provider、跨成本中心與跨團隊治理。

## 操作成本

CloudHealth 的主要成本是組織模型維護。Business unit、cost center、application、environment、owner、account 與 tag policy 需要持續治理，平台才能提供穩定報表。

流程成本會高於單純報表工具。Recommendation 需要進入 approval、exception、change management、validation 與 financial close process；這些流程讓工具適合大型組織，也要求更高維運紀律。

資料品質成本會集中在標籤與 shared cost。未標記資源、跨團隊 shared service、commitment benefit 分攤與 marketplace charge 都會影響成本歸屬信任度。

## Evidence Package

CloudHealth 結果應回寫到 FinOps governance evidence package。最小欄位包括 business unit、cost center、application、provider、account、policy、recommendation、expected saving、approval state、implementation state、verified saving 與 exception。

| 欄位         | CloudHealth 證據來源                                   |
| ------------ | ------------------------------------------------------ |
| Source       | cost report、policy report、recommendation queue       |
| Time range   | billing period、review cycle、saving validation window |
| Query link   | CloudHealth report、cloud billing query、policy detail |
| Data quality | tag compliance、account coverage、allocation rule      |
| Confidence   | owner mapping、approval status、verified saving        |
| Known gap    | shared service rule、manual exception、provider delay  |

Evidence package 的核心用途是支援治理審查。CloudHealth report 要能回答「這筆成本屬於誰、哪條 policy 觸發、誰核准例外、變更是否真的帶來 savings」。

## 案例回寫

CloudHealth 目前適合作為 enterprise FinOps 與多雲治理案例的工具承接點。它可回寫到 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 的 7 個受監管市場跨地區治理與成本中心分攤需求、[9.C33 Maersk + Bosch on Azure AKS](/backend/09-performance-capacity/cases/maersk-bosch-azure-aks/) 的傳統產業多 BU 治理一致性、[9.C22 Wayfair hybrid burst](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/) 的 on-prem + GCP 雙來源帳單合併、以及 [9.C35 Snap multi-cloud](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/) 的 GCP + AWS 跨雲成本對照。

這些案例的重點是組織能力。CloudHealth 頁引用案例時，要把案例拆成 governance model、owner taxonomy、policy action、engineering validation 與 financial reporting — 例如 Standard Chartered 的 7 市場分割要回到 per-market policy + 合規 tag、不是單一全球 report、而非停在雲端帳單下降。

## 下一步路由

- 上游：[9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/)
- 上游：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)
- 跨模組：[04 可觀測性成本歸因](/backend/04-observability/cost-attribution/)
- 平行：[Vantage](/backend/09-performance-capacity/vendors/vantage/)
- 官方：[Broadcom CloudHealth announcement](https://news.broadcom.com/apj/releases/broadcom-announces-new-cloudhealth-user-experience-for-greater-cloud-spend-management-across-enterprise-teams)
