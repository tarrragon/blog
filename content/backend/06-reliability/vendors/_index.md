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
