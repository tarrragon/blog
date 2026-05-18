---
title: "可靠性 Vendor 清單"
date: 2026-05-01
description: "規劃 CI、壓測、chaos engineering 與 SLO 工具的服務頁撰寫順序與判準"
weight: 91
tags: ["backend", "reliability", "vendor"]
---

可靠性 Vendor 清單的核心責任是把工具名稱放回 verification loop、release gate、fault injection、SLO governance 與 evidence handoff 的判斷。每個服務頁先回答它承擔哪一種可靠性驗證責任，再討論整合成本、風險控制、artifact 與案例回寫。

跟 [cases/](/backend/06-reliability/cases/) 是不同維度。Cases 是教學案例來源，vendors 是把驗證流程落地的工具入口。

## 讀法

可靠性工具要從驗證流程進入。讀者如果要處理 release gate，先回到 [6.8 Release Gate](/backend/06-reliability/release-gate/)；如果要處理 load test 與 regression，先回到 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)；如果要處理 chaos，先回到 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。

## T1 服務頁大綱

| 服務                                                              | 類型              | 頁面要回答的核心問題                                                       |
| ----------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------- |
| [GitHub Actions](/backend/06-reliability/vendors/github-actions/) | CI/CD             | workflow、environment、artifact 與 approval gate 如何支援 release evidence |
| [CircleCI](/backend/06-reliability/vendors/circleci/)             | CI/CD             | pipeline、orb、parallelism 與 context 權限如何取捨                         |
| [k6](/backend/06-reliability/vendors/k6/)                         | Load test         | scenario、threshold 與 CI gate 如何支援可靠性驗證                          |
| [Gatling](/backend/06-reliability/vendors/gatling/)               | Load test         | JVM simulation、injection profile 與 report 如何支援 regression gate       |
| [JMeter](/backend/06-reliability/vendors/jmeter/)                 | Load test         | GUI plan、protocol sampler 與既有測試資產如何治理                          |
| [Locust](/backend/06-reliability/vendors/locust/)                 | Load test         | Python user behavior 與 distributed worker 如何支援自訂 workload           |
| [Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/)         | Chaos engineering | Kubernetes-native fault injection 與 experiment scope 如何控制             |
| [LitmusChaos](/backend/06-reliability/vendors/litmuschaos/)       | Chaos engineering | chaos workflow、hub 與 Kubernetes 實驗治理如何取捨                         |
| [Gremlin](/backend/06-reliability/vendors/gremlin/)               | Chaos platform    | 商業 chaos 平台、blast radius guardrail 與審計如何支援成熟團隊             |
| [Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)           | Fault injection   | TCP fault、local integration test 與 dependency failure 如何模擬           |
| [Nobl9](/backend/06-reliability/vendors/nobl9/)                   | SLO platform      | SLO、error budget、alerting 與 governance 如何整合                         |
| [Sloth](/backend/06-reliability/vendors/sloth/)                   | SLO generator     | OpenSLO / Prometheus rule 生成如何降低 SLO 維護成本                        |

## 服務頁撰寫欄位

| 欄位     | 可靠性服務頁要保留的問題                                                        |
| -------- | ------------------------------------------------------------------------------- |
| 服務責任 | 它承擔 CI gate、load test、chaos、fault injection 還是 SLO governance           |
| 適用壓力 | release frequency、failure mode、experiment safety、SLO maturity 哪個壓力最明顯 |
| 替代邊界 | CI 平台、09 壓測工具、chaos 平台、SLO tool 的機會成本                           |
| 操作成本 | runner、secret、artifact、test data、blast radius、experiment approval          |
| Evidence | workflow run、test report、experiment result、SLO burn、gate decision           |
| 案例回寫 | Google SRE、Netflix chaos、release gate 與 replay 案例如何提供判準              |

## 服務頁標準章節

| 章節                 | 可靠性工具頁要補的內容                                                             |
| -------------------- | ---------------------------------------------------------------------------------- |
| 工具定位             | 它是 CI gate、load test、chaos platform、fault injection 還是 SLO governance       |
| 本章目標             | 讀者能判斷該工具能產生哪種 verification evidence 與 gate decision                  |
| 最短判讀路徑         | 用「要擋 release、驗證負載、注入失敗、追 SLO」快速定位工具類型                     |
| 日常操作與決策形狀   | workflow、runner、secret、artifact、approval、experiment scope、SLO rule           |
| 核心取捨表           | CI 平台、09 壓測工具、chaos 平台、SLO 平台的機會成本                               |
| 進階主題             | self-hosted runner、blast radius guardrail、error budget policy、audit             |
| 排錯與失敗快速判讀   | flaky job、missing artifact、unsafe experiment、false SLO alert、runner bottleneck |
| 何時改走其他服務     | 容量模型回 09、觀測資料回 04、事故協作回 08、部署控制回 05                         |
| 不在本頁內的主題     | 完整 pipeline cookbook、每個 test framework、所有 chaos experiment 範本            |
| 案例回寫與下一步路由 | 回到 06 cases、6.8 release gate、6.20 experiment safety boundary                   |

## 跨 vendor 議題對照

本模組 12 個 vendor 跨 4 個 sub-category（CI/CD / load test / chaos / SLO）、不是同類選一。對照表用「橫向 reliability gate 議題」標明每個議題在哪個 sub-category 落地。

| 議題         | GH Actions    | CircleCI    | k6          | Gatling          | JMeter       | Locust      | Chaos Mesh     | Litmus     | Gremlin      | Toxiproxy   | Nobl9          | Sloth         |
| ------------ | ------------- | ----------- | ----------- | ---------------- | ------------ | ----------- | -------------- | ---------- | ------------ | ----------- | -------------- | ------------- |
| 主責任       | CI gate       | CI gate     | Load test   | Load test        | Load test    | Load test   | K8s chaos      | K8s chaos  | 跨平台 chaos | TCP fault   | SLO governance | SLO generator |
| 整合 CI gate | 原生          | 原生        | threshold   | assertion        | non-GUI mode | headless    | workflow       | workflow   | scenario     | client SDK  | error budget   | rule gen      |
| 配置模式     | YAML          | YAML        | JS          | Scala / Java     | XML GUI      | Python      | CRD            | CRD        | UI / API     | API         | YAML / UI      | YAML          |
| 環境支援     | GitHub-hosted | cross-VCS   | OSS / Cloud | OSS / Enterprise | OSS          | OSS         | K8s only       | K8s only   | 跨平台       | TCP layer   | multi-source   | Prometheus    |
| 進階產出     | matrix / OIDC | parallelism | extension   | feeder           | plugins      | distributed | scope control  | ChaosHub   | GameDay      | toxic types | composite SLO  | multi-burn    |
| 商業 / 開源  | 商業 + SaaS   | 商業 + SaaS | OSS + Cloud | OSS + Enterprise | OSS          | OSS         | OSS            | OSS + 商業 | 商業 SaaS    | OSS         | 商業 SaaS      | OSS           |
| 主討論案例   | 待補          | 待補        | 待補        | 待補             | 待補         | 待補        | Netflix/Google | 待補       | 待補         | Shopify     | Google SRE     | 待補          |

對照表的用途有三：

- 寫某 vendor 頁時、看相同 sub-category 對手如何處理同一議題
- 讀者組 reliability stack：CI gate + load test + chaos + SLO 各選 1
- 評估 OSS vs 商業 trade-off

下面 4 段把對照表的 sub-category 展開、不是每行都展開。

### CI gate（GitHub Actions / CircleCI）

CI gate 是 release 前最後一道驗證、決定哪些工件可發。**GitHub Actions** 跟 GitHub 深度整合（PR check / environment protection / OIDC cloud auth）、marketplace action 生態最廣；**CircleCI** 強進階 cache + parallelism + macOS / GPU resource class、cross-VCS（GitHub / Bitbucket / GitLab）。

選型判讀：GitHub-hosted + 普通用 → GitHub Actions；極致 build speed / macOS / 跨 VCS → CircleCI；複雜 DAG → Tekton / Argo。

### Load test（k6 / Gatling / JMeter / Locust）

Load test 提供 performance regression evidence。差異主要在語言生態：**k6** JS / CLI-first / Grafana 生態；**Gatling** Scala / Java / 強型別 / 複雜 scenario；**JMeter** GUI / 老牌 / 多 protocol；**Locust** Python / 自訂邏輯極彈性。

選型判讀：CI-first JS → k6；JVM 生態 → Gatling；既有 .jmx 資產 → JMeter；Python 團隊 / 複雜邏輯 → Locust。詳見 [9 performance capacity 模組](/backend/09-performance-capacity/) 的 capacity planning 角度。

### Chaos engineering（Chaos Mesh / LitmusChaos / Gremlin / Toxiproxy）

Chaos 工具按 scope 跟運維模式分四類：**Chaos Mesh** K8s-native CRD-driven 多 fault types；**LitmusChaos** K8s + ChaosHub experiment 庫；**Gremlin** 商業 SaaS / 跨平台 / GameDay；**Toxiproxy** TCP-level / integration test 用。

選型判讀：K8s production + OSS → Chaos Mesh / Litmus；跨平台 + 商業 → Gremlin；CI integration test → Toxiproxy。對應 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/) 的 blast radius 設計。

### SLO governance（Nobl9 / Sloth）

SLO 工具按 source 跟運維模式分兩類：**Nobl9** 商業 SaaS / multi-source / OpenSLO 主導 / 企業 governance；**Sloth** OSS / Prometheus-only / 產生 Prometheus rules。

選型判讀：multi-source / SaaS / governance → Nobl9；Prometheus-only / OSS → Sloth / Pyrra；vendor 內建夠 → Datadog SLO / Grafana SLO / Honeycomb SLO。對應 [knowledge cards burn-rate](/backend/knowledge-cards/burn-rate/)。

## 撰寫批次

| 批次 | 服務頁                                         | 撰寫目的                                                  |
| ---- | ---------------------------------------------- | --------------------------------------------------------- |
| R1   | GitHub Actions / CircleCI                      | 建立 CI gate、artifact 與 approval baseline               |
| R2   | k6 / Gatling / JMeter / Locust                 | 建立可靠性驗證視角的壓測工具對照                          |
| R3   | Chaos Mesh / LitmusChaos / Gremlin / Toxiproxy | 建立 fault injection 與 experiment safety 對照            |
| R4   | Nobl9 / Sloth                                  | 建立 SLO governance、error budget 與 rule generation 判準 |

## 後續候選

| 類型                | 候選服務                                                        | 寫作重點                                                     |
| ------------------- | --------------------------------------------------------------- | ------------------------------------------------------------ |
| CI/CD               | GitLab CI、Jenkins、Buildkite、Tekton、Harness、Azure Pipelines | self-hosted runner、enterprise workflow、pipeline governance |
| Load / browser gate | Artillery、Grafana k6 Cloud、BlazeMeter、Playwright、Cypress    | managed runner、browser flow、release gate、cost             |
| Chaos / fault       | AWS Fault Injection Service、Azure Chaos Studio、Pumba          | cloud-native fault、container fault、blast radius            |
| SLO                 | Pyrra、OpenSLO、Keptn                                           | Prometheus-native SLO、portable SLO spec、quality gate       |
| Policy / audit      | Steampipe、Conftest                                             | compliance query、control evidence、change review            |

主流覆蓋檢查的重點是分開 CI gate、performance gate、chaos gate、SLO gate 與 policy gate。CI 工具負責 release artifact 與 approval；load / browser 工具負責 regression evidence；chaos 工具負責 failure mode evidence；SLO 工具負責 error budget governance；policy 工具負責控制證據。

## 下一步路由

- 上游：[6.8 Release Gate](/backend/06-reliability/release-gate/)
- 上游：[6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 平行：[09 效能與容量工具清單](/backend/09-performance-capacity/vendors/)
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
