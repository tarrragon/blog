---
title: "效能與容量工具清單"
date: 2026-05-15
description: "整理效能工程、容量規劃、壓測、production replay 與 profiling 工具的服務責任與選型路由"
weight: 90
tags: ["backend", "performance", "capacity", "vendor", "tools"]
---

效能與容量工具清單的核心責任是把工具名稱放回 workload model、saturation discovery、capacity planning 與 production validation 的服務責任。工具頁先回答它降低哪一種風險，再討論 scenario scripting、distributed load、結果保存、CI 整合、成本與案例回寫。

## 讀法

效能工具要從問題節點進入。團隊如果缺 workload model，先讀 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)；如果缺 saturation 邊界，先讀 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)；如果缺 production 驗證，先讀 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)。

工具頁的任務是承接這些問題節點。k6、JMeter、Gatling、Locust 與 Vegeta 都能產生負載，但它們在腳本語言、protocol 覆蓋、分散式執行、CI integration、報表與團隊學習成本上不同；production replay、profiling 與 cost analysis 工具則承擔不同的證據責任。

## T1 工具頁

| 工具                                                                                                 | 類型           | 核心責任                                                     |
| ---------------------------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------ |
| [k6](/backend/09-performance-capacity/vendors/k6/)                                                   | Load test      | 用 scriptable scenario 建立 API / protocol 負載              |
| [JMeter](/backend/09-performance-capacity/vendors/jmeter/)                                           | Load test      | 用 GUI、plugin 與多 protocol sampler 承接企業測試資產        |
| [Gatling](/backend/09-performance-capacity/vendors/gatling/)                                         | Load test      | 用 JVM DSL 與 injection profile 表達複雜 scenario            |
| [Locust](/backend/09-performance-capacity/vendors/locust/)                                           | Load test      | 用 Python user behavior 與 distributed worker 表達高自訂負載 |
| [Vegeta](/backend/09-performance-capacity/vendors/vegeta/)                                           | HTTP probe     | 用固定 rate HTTP attack 快速探測 endpoint saturation         |
| [GoReplay](/backend/09-performance-capacity/vendors/goreplay/)                                       | Traffic replay | 捕捉 production HTTP traffic 並重播到 shadow target          |
| [Service Mesh Mirroring](/backend/09-performance-capacity/vendors/service-mesh-mirroring/)           | Traffic mirror | 用 proxy route policy mirror production traffic              |
| [AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/)     | Traffic mirror | 用 VPC 網路層封包鏡像建立低侵入 production evidence          |
| [Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/) | Profiling      | 用 SaaS APM 整合與 deploy marker 支援 profile diff           |
| [Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/)                                     | Profiling      | 用 Grafana / OSS profiling backend 建立可自管 profile diff   |
| [Parca](/backend/09-performance-capacity/vendors/parca/)                                             | Profiling      | 用 eBPF 與平台視角建立 infrastructure-wide profile evidence  |
| [Akamas](/backend/09-performance-capacity/vendors/akamas/)                                           | Optimization   | 用 SLO constraint 與配置實驗建立 capacity / cost 調校閉環    |
| [Vantage](/backend/09-performance-capacity/vendors/vantage/)                                         | FinOps         | 用 cost reports、Kubernetes cost 與 forecast 建立成本可見性  |
| [CloudHealth](/backend/09-performance-capacity/vendors/cloudhealth/)                                 | FinOps         | 用 enterprise governance、policy 與 allocation 管理雲端成本  |
| [AWS Cost Explorer](/backend/09-performance-capacity/vendors/aws-cost-explorer/)                     | AWS FinOps     | 用 AWS-native cost / usage report 建立成本分析 baseline      |

這批工具頁已完成 load test、production traffic replay、continuous profiling 與 capacity / cost analysis 的主要分流。k6 承接 scriptable scenario，JMeter 承接企業測試資產，Gatling 承接 JVM simulation，Locust 承接 Python custom behavior，Vegeta 承接快速 HTTP probe；GoReplay、Service Mesh Mirroring 與 AWS VPC Traffic Mirroring 承接不同層級的 production traffic evidence；Datadog Continuous Profiler、Pyroscope 與 Parca 承接不同操作模型的 profile evidence；Akamas、Vantage、CloudHealth 與 AWS Cost Explorer 承接 cost visibility、optimization 與 FinOps governance。

## 內容覆蓋進度

每個工具頁下會擴充兩類文章：deep article（工具自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨工具遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「← X」代表從 X 遷入。

| Vendor                                                      | Deep article | Migration playbook                                                          |
| ----------------------------------------------------------- | ------------ | --------------------------------------------------------------------------- |
| [k6](k6/)                                                   | —            | [← JMeter (Type E)](k6/migrate-from-jmeter/)                                |
| [Datadog Continuous Profiler](datadog-continuous-profiler/) | —            | [← Pyroscope (Type C)](datadog-continuous-profiler/migrate-from-pyroscope/) |

其他 T1 工具（JMeter / Gatling / Locust / Vegeta / GoReplay / Service Mesh Mirroring / AWS VPC Traffic Mirroring / Pyroscope / Parca / Akamas / Vantage / CloudHealth / AWS Cost Explorer）尚未開始。跟 [06 vendors](/backend/06-reliability/vendors/) 共用部分工具（k6 / JMeter / Gatling / Locust），未來寫 deep article 時需明確區分「驗證流程的工具鏈」（06）跟「效能工程的工具鏈」（09）的角度。對應的 backlog 議題見上方「T1 工具頁」段每個工具頁要回答的核心責任、跟各工具 `_index.md` 的「預計實作話題」段。

## 後續候選

| 類型                       | 候選工具                                                                                                                | 寫作重點                                                   |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Load test                  | Artillery、wrk、hey、Grafana k6 Cloud、AWS Distributed Load Testing、BlazeMeter、LoadRunner                             | managed runner、跨 region、報表與費用                      |
| Production traffic replay  | shadow traffic pattern、Diffy 類 response diff、proxy mirror variants                                                   | response diff、資料遮罩、side effect 邊界                  |
| Profiling                  | GCP Cloud Profiler、AWS CodeGuru Profiler、Azure Application Insights Profiler、New Relic Profiler、Dynatrace Profiling | 雲端整合、採樣成本、profile diff                           |
| Capacity / cost analysis   | Kubecost / OpenCost、CloudZero、CAST AI、Infracost、Harness Cloud Cost Management                                       | workload-level 成本、rightsizing、IaC cost                 |
| Benchmark / workload model | YCSB、JMH、pgbench、sysbench                                                                                            | component benchmark、DB workload、micro vs system boundary |

Load test 工具頁要保留 workload model 語言。JMeter 適合 protocol 覆蓋與 GUI 驅動團隊，Gatling 適合程式化 scenario 與 JVM 生態，Locust 適合 Python 團隊，Vegeta 適合簡單 HTTP 壓測與 CLI workflow。

Production replay 工具頁要保留安全與副作用邊界。Replay production traffic 會碰到 PII、credential、payment callback、idempotency 與下游配額，因此文章要先定義遮罩、隔離、rate limit 與 stop condition。

Profiling 工具頁要保留長期成本。Continuous profiling 能降低退化定位時間，但會增加採樣成本、儲存成本、敏感資訊治理、symbolization 與 baseline 維護責任。

Capacity / cost analysis 工具頁要保留 owner 與行動閉環。成本報表只有在 tag、label、cost center、service owner、release marker 與 action workflow 對齊後，才會變成容量規劃與成本改善的工程證據。

主流覆蓋檢查的重點是分開 scenario load、quick probe、managed runner、traffic replay、profiling、FinOps 與 component benchmark。k6 / Gatling / Locust 解 scenario；Vegeta / wrk / hey 解 quick HTTP probe；Grafana k6 Cloud / AWS Distributed Load Testing / BlazeMeter 解 managed runner；Pyroscope / Parca / Datadog / cloud profiler 解 profiling；Kubecost / CloudZero / CAST AI 解 workload cost。

## 工具頁標準章節

| 章節                 | 效能與容量工具頁要補的內容                                                       |
| -------------------- | -------------------------------------------------------------------------------- |
| 工具定位             | 它是 load test、replay、traffic mirror、profiler、optimizer 還是 FinOps 工具     |
| 本章目標             | 讀者能判斷它降低容量未知、production gap、瓶頸定位或成本歸因哪種風險             |
| 最短判讀路徑         | 用「缺 workload、缺 saturation、缺 production evidence、缺 cost owner」快速定位  |
| 日常操作與決策形狀   | scenario、runner、threshold、sampling、dashboard、recommendation、owner          |
| 核心取捨表           | 同類工具與相鄰工具的機會成本，例如 k6 vs JMeter、Vantage vs Cost Explorer        |
| 進階主題             | distributed runner、shadow traffic、continuous profiling、optimization guardrail |
| 排錯與失敗快速判讀   | runner bottleneck、side effect、sampling bias、tag gap、forecast drift           |
| 何時改走其他服務     | 驗證流程回 06、觀測資料回 04、部署控制回 05、事故處理回 08                       |
| 不在本頁內的主題     | 完整工具 CLI 教學、供應商 pricing 細節、所有 dashboard 設定                      |
| 案例回寫與下一步路由 | 回到 09 cases、6.13 regression gate、4.20 evidence package                       |

## 跨 vendor 議題對照

本模組 15 個 vendor 跨 5 個 sub-category（load test / production replay / continuous profiling / optimization / FinOps）、解不同效能與容量工程問題、不是同類選一。

| Sub-category         | 典型 vendor                                 | 輸出證據                                   | Production 風險                | 操作成本                                 | Owner             |
| -------------------- | ------------------------------------------- | ------------------------------------------ | ------------------------------ | ---------------------------------------- | ----------------- |
| Load test            | k6 / JMeter / Gatling / Locust / Vegeta     | threshold pass/fail / p95 p99 / throughput | 低（測試環境）                 | scenario 維護 / runner 規模 / 測試資料   | Engineering / QA  |
| Production replay    | GoReplay / Service Mesh Mirroring / AWS VPC | response diff / shadow load                | 高（PII / side effect / 配額） | masking / isolation / rate limit         | SRE + Security    |
| Continuous profiling | Datadog Profiler / Pyroscope / Parca        | flame graph diff / regression detection    | 中（採樣 overhead）            | symbolization / storage / baseline 維護  | Engineering       |
| Optimization         | Akamas                                      | recommendation / SLO-constrained config    | 中（autopilot rollout）        | objective model / approval workflow      | SRE + FinOps      |
| FinOps               | Vantage / CloudHealth / AWS Cost Explorer   | cost report / forecast / rightsizing       | 無(reporting)                  | tag governance / owner mapping / cadence | FinOps + Eng lead |

對照表的用途有三：

- 對齊 sub-category 跟問題節點：缺 saturation → load test；缺 production gap → replay；缺 瓶頸定位 → profiler；缺 capacity / cost 閉環 → optimizer + FinOps
- 評估 production 風險：load test 安全、replay / mirror 要明示 side effect 邊界、profiler 要看採樣 overhead、FinOps reporting 無風險
- 對齊 owner：load test 多 Engineering / QA、replay 多 SRE + Security、optimization + FinOps 跨團隊

下面 5 段把對照表的 sub-category 展開、每段帶 vendor 選型判讀。

### Load test（k6 / JMeter / Gatling / Locust / Vegeta）

Load test 是 09 模組的主要 saturation 探測工具、跟 [06 reliability load test 章節](/backend/06-reliability/vendors/) 同 vendor 但角度不同 — 06 看 CI gate / regression evidence、09 看 capacity planning / saturation discovery / peak event readiness。

選型判讀：CI-first JS → [k6](/backend/09-performance-capacity/vendors/k6/)；JVM + 複雜 scenario → [Gatling](/backend/09-performance-capacity/vendors/gatling/)；既有 .jmx 資產 → [JMeter](/backend/09-performance-capacity/vendors/jmeter/)；Python custom behavior → [Locust](/backend/09-performance-capacity/vendors/locust/)；快速 HTTP probe / fixed rate → [Vegeta](/backend/09-performance-capacity/vendors/vegeta/)（單一 HTTP attack 模式、不適合多 step scenario）。

### Production replay（GoReplay / Service Mesh Mirroring / AWS VPC Traffic Mirroring）

Production replay 把實際流量重播到 shadow target、補 load test 的「人工 scenario 跟真實流量差距」缺口。**GoReplay** 應用層 HTTP traffic capture + replay；**Service Mesh Mirroring** 用 Envoy / Istio proxy mirror、適合 K8s 內部；**AWS VPC Traffic Mirroring** L4 封包鏡像、適合非 HTTP / 低侵入。

選型判讀：HTTP application 層 → GoReplay；K8s 內 service mesh → Service Mesh Mirroring；非 HTTP / 跨 VPC / 低侵入 → AWS VPC。共同議題：PII 遮罩、idempotency boundary、downstream 配額 — 不可省。

### Continuous profiling（Datadog Continuous Profiler / Pyroscope / Parca）

Continuous profiling 在 production 持續採樣、退化時可 profile diff 找瓶頸。**Datadog Continuous Profiler** SaaS APM 整合、deploy marker 自動關聯；**Pyroscope** OSS / Grafana 生態、可自管或 Grafana Cloud；**Parca** eBPF-based、infrastructure-wide profile（不需 application instrumentation）。

選型判讀：已用 Datadog APM → Datadog Profiler；Grafana 生態 / OSS → Pyroscope；不想 instrument application + eBPF 友善 → Parca。共同議題：採樣 overhead（CPU / memory）、symbolization、storage cost、敏感資訊。

### Optimization（Akamas）

Optimization 把 workload + SLO + cost 放進同一閉環、產出 configuration recommendation。**Akamas** 是 09 模組唯一 optimizer vendor、適合已有可量測 workload 跟成本壓力的服務。

選型判讀：Kubernetes rightsizing + runtime tuning + cost target → Akamas；純 FinOps reporting 不夠（要主動建議）→ Akamas。Akamas 不替代 FinOps tool — Vantage / CloudHealth 看歷史成本、Akamas 提產出未來 recommendation。

### FinOps（Vantage / CloudHealth / AWS Cost Explorer）

FinOps 提供 cost visibility + forecast + allocation。**Vantage** Kubernetes cost + forecast 友善的 startup-friendly 平台；**CloudHealth** enterprise FinOps governance + policy + chargeback；**AWS Cost Explorer** AWS-native cost analysis baseline（免費、限 AWS）。

選型判讀：純 AWS 啟動 → Cost Explorer；多雲 + startup / mid-size → Vantage；enterprise + 多 BU chargeback → CloudHealth；K8s workload cost → Kubecost / OpenCost（不在本表、後續候選）。共同議題：tag governance、cost center mapping、cadence。

## 下一步路由

- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 上游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 平行：[06 Reliability vendors](/backend/06-reliability/vendors/) — 06 從驗證流程看工具，09 從容量量化與效能工程看工具
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
