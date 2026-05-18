---
title: "CloudHealth"
date: 2026-05-15
description: "用 enterprise FinOps governance、policy 與多雲成本管理支援大型組織的容量成本治理"
weight: 22
tags: ["backend", "performance", "capacity", "vendor", "cloudhealth", "finops"]
---

CloudHealth 的核心責任是把大型組織的 cloud spend、governance、policy、allocation 與 optimization workflow 放進同一個 FinOps 管理平面。它適合 account、team、business unit、provider 與採購流程複雜的組織，重點在讓成本治理、合規要求與工程 owner 能共用同一套成本事實。2018 年被 VMware 收購、2023 年隨 VMware 進入 Broadcom 旗下；現屬 Broadcom 的 enterprise FinOps 旗艦產品。

## 服務定位

CloudHealth 跟 AWS Cost Explorer / Azure Cost Management 那種單雲原生工具的差異不在 *單雲帳單細節*、而在 *跨雲一致 schema + enterprise FinOps operating model*。Cost Explorer 在 AWS-only 場景的 granularity 更深、但跨 Azure / GCP 帳單對齊、成本中心 chargeback、policy 治理就需要 CloudHealth 這類 multi-cloud platform。

跟 Vantage 比、CloudHealth 走 *enterprise governance-first*、Vantage 走 *engineering-friendly dashboard-first*。Vantage 對小到中型 cloud-native 團隊更快上手、但 chargeback 流程、policy violation queue、approval workflow 都不是它的主場。跟 Apptio Cloudability（IBM 收購）比、兩者定位最接近、都吃 large enterprise FinOps 市場；CloudHealth 的差異是 VMware / Broadcom ecosystem 整合（vCenter / Tanzu / on-prem hybrid），Cloudability 強在 TBM（Technology Business Management）財務分攤模型成熟度。

關鍵張力：*Broadcom 收購後的 product roadmap 不確定性* ↔ *enterprise FinOps ecosystem 深度*。Broadcom 對 VMware portfolio 的價格調整、partner 縮編、support tier 變動 2024-2025 持續發生；客戶要評估 *退場成本（chargeback rule + tag taxonomy 量大）vs 短期 license 漲幅*、不是只看當下功能。

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

## 最短判讀路徑

判斷 CloudHealth deployment 是否健康、最少看四件事：

- **Multi-cloud connector 完整性**：AWS（CUR / billing role）、Azure（EA / MCA billing role）、GCP（BigQuery billing export）、Kubernetes（kube-state-metrics + Prometheus）連接器是否都接通、是否有 daily ingestion lag、是否漏 account / subscription
- **FinOps team workflow 落地**：policy queue、recommendation queue、approval flow 是否有實際 owner（不只是 dashboard 看一看）、weekly / monthly FinOps cadence 是否進到工程 sprint 跟財務 close cycle
- **Chargeback 規則可對帳**：business unit / cost center / application / environment 的分攤公式是否文件化、shared service（platform team / CI runner / observability stack）的 split rule 是否被各 BU 接受、月底財務 close 對得起來
- **Reserved Instance / Savings Plan 管理**：commitment coverage（已 commit 比例）、utilization（已用比例）、expiration alert、跨 account 的 commitment sharing 是否有 owner 主動經營、不是買完就放著

四件事任一缺失、就是 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/) 邊界的待補項目。

## 核心取捨表

| 取捨維度     | CloudHealth                      | Vantage                          | AWS Cost Explorer          | Apptio Cloudability        |
| ------------ | -------------------------------- | -------------------------------- | -------------------------- | -------------------------- |
| Multi-cloud  | 強 — AWS / Azure / GCP / K8s     | 強 — 加 Snowflake / Datadog 整合 | 弱 — AWS-only              | 強 — 三大雲 + on-prem      |
| 學習曲線     | 陡 — enterprise model 複雜       | 緩 — engineer 友善 dashboard     | 緩 — AWS console 內建      | 陡 — TBM 模型門檻高        |
| Chargeback   | 強 — policy + approval flow 完整 | 中 — report-driven、流程靠外掛   | 弱 — 報表為主、無 workflow | 強 — TBM 財務分攤是主場    |
| 部署模型     | SaaS only                        | SaaS only                        | AWS console 內建           | SaaS only                  |
| 適合規模     | Enterprise（多 BU + 多雲）       | Startup ~ Mid（cloud-native）    | AWS single-account ~ Org   | Enterprise（重財務治理）   |
| 計費模型     | % of cloud spend + minimum       | Per-cloud-account tier           | Free（AWS 內建）           | % of cloud spend + minimum |
| Roadmap 風險 | Broadcom 收購後不確定            | 獨立公司、roadmap 穩定           | AWS 自家、roadmap 跟雲同步 | IBM 收購後整合中           |
| 退場成本     | 高 — chargeback rule + tag 量大  | 低 — report 可重建               | 無 — AWS-native 切換無痛   | 高 — TBM 模型重 migrate    |

選 CloudHealth 的核心訴求：*enterprise scale + 多雲 + 已有 VMware / Broadcom ecosystem*、且能投入 FinOps team 維護 chargeback rule、policy queue、commitment management lifecycle。中小型 cloud-native 走 Vantage 更快；AWS-only 直接用 Cost Explorer + Cost Anomaly Detection；重財務 TBM 整合走 Apptio Cloudability。

## 跟其他工具的取捨

CloudHealth 和 Vantage 的主要差異是治理深度。Vantage 偏工程友善報表與 Kubernetes cost visibility；CloudHealth 偏 enterprise FinOps operating model、policy 與大組織分攤流程。

CloudHealth 和 Akamas 的主要差異是最佳化方式。CloudHealth 偏成本治理與推薦流程；Akamas 偏把 SLO 約束與 configuration tuning 放進 optimization engine。

CloudHealth 和 AWS Cost Explorer 的主要差異是多雲與流程。Cost Explorer 適合 AWS-native 成本分析；CloudHealth 適合跨 provider、跨成本中心與跨團隊治理。

## 操作成本

CloudHealth 的主要成本是組織模型維護。Business unit、cost center、application、environment、owner、account 與 tag policy 需要持續治理，平台才能提供穩定報表。

流程成本會高於單純報表工具。Recommendation 需要進入 approval、exception、change management、validation 與 financial close process；這些流程讓工具適合大型組織，也要求更高維運紀律。

資料品質成本會集中在標籤與 shared cost。未標記資源、跨團隊 shared service、commitment benefit 分攤與 marketplace charge 都會影響成本歸屬信任度。

## 進階主題

**Reserved Instance 與 Savings Plan management**：CloudHealth 把 commitment 視為 portfolio、不是單筆採購。Coverage（已 commit 比例）、utilization（已用比例）、break-even（攤平時間）三個指標要持續追、跟業務 roadmap 對齊；新服務上線前先 model 預期用量、commit 太多反而 lock-in 浪費、太少又付 on-demand 溢價。跨 account / linked account 的 commitment sharing 要明確 owner、不然 platform team 買的 RI 被 product team 吃掉、財務分攤回不去。

**Chargeback / showback 流程**：showback 是 *讓 BU 看到自己花多少*、chargeback 是 *讓 BU 帳本上真的扣這筆*。chargeback 需要財務簽核、需要每月 close cycle、需要 dispute 機制；CloudHealth 的 chargeback rule 改動要走 approval、不能 admin 自己改完就上線、會直接影響 BU 月結。

**Multi-cloud asset inventory**：CloudHealth 不只是帳單工具、也作 asset inventory — EC2 / RDS / VM / GKE node / Azure SQL 等資源的 owner、tag、environment、policy state 在同一視角。這個能力是 enterprise CMDB integration 的入口、也能反向支援 [7 security posture](/backend/07-security-data-protection/) 的 untagged / unauthorized resource 偵測。

**跟 Datadog / SIEM integration**：CloudHealth 的 cost data 可以 export 到 [Datadog](/backend/04-observability/vendors/datadog/) 作 SRE cost-aware alert（service 突然花費暴衝 → 通常是 retry storm / runaway job），也可送 SIEM 作 untagged resource / cross-account spend anomaly 偵測。整合的價值不是把 CloudHealth 當另一個 observability tool、而是讓 cost signal 進到工程值班的視野。

**Broadcom 收購後 product roadmap 變動風險**：2023 Broadcom 完成 VMware 收購後、CloudHealth 經歷 license model 調整、partner program 變動、support tier 重整。對既有大客戶來說 license 漲幅、SLA 條款、roadmap 透明度都進入再評估期；新客戶選型時 *退場成本評估* 要先做、不能假設 platform 五年不變。Broadcom 對 enterprise 客戶仍會維持產品線、但中小客戶可能感受到 support 縮減。

## 排錯與失敗快速判讀

- **Multi-cloud tag 不一致**：AWS 用 `Environment=prod`、Azure 用 `env=production`、GCP 用 `env-tier=prod` — CloudHealth 報表看起來三套不同 — 統一 tag taxonomy（cost center / application / environment / owner）寫進 cloud governance policy、用 cloud-native enforcement（AWS Tag Policy / Azure Policy / GCP Org Policy）擋未標記資源
- **Chargeback 對不上帳**：BU 看到的金額 ≠ 財務 close 的金額 — shared service split rule 沒被簽核、commitment benefit attribution 跑掉、marketplace charge 沒分攤 — 走 monthly close reconciliation、把 rule 鎖定後才開 dispute window
- **Reserved Instance 浪費**：commit 買了沒用滿（utilization < 80%）— 跨 account share 沒開、或業務 roadmap 改了沒同步 commitment team — 開 cross-account RI sharing、commitment review 進 monthly FinOps cadence
- **新雲帳號接不進來**：connector 一直 ingestion failure — IAM role / EA permission / BigQuery export 沒設好、或 organization 結構改了 CloudHealth 沒同步 — 走 onboarding checklist、新 account 自動化納管
- **Recommendation 一直沒人 action**：rightsizing queue 累積幾百筆沒處理 — 沒有 owner、或 recommendation 沒對應到實際 service team — 用 tag 反查 owner、把 recommendation 進 sprint backlog 而非 FinOps 自己追
- **Broadcom 收購後 support / price 變動**：renewal 漲幅突然 30-50%、support tier 被降級 — 早一年開始評估替代方案（Vantage / Apptio / 雲原生組合）、把 chargeback rule 跟 tag taxonomy 抽象到不綁 vendor 的格式

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
