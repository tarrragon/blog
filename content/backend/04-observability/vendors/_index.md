---
title: "可觀測性 Vendor 清單"
date: 2026-05-01
description: "規劃 telemetry standard、metrics、logs、traces、APM 與 error tracking 的服務頁撰寫順序與判準"
weight: 90
tags: ["backend", "observability", "vendor"]
---

可觀測性 Vendor 清單的核心責任是把工具名稱放回 telemetry contract、signal ownership、data quality、cardinality 與成本治理的判斷。每個服務頁先回答它承擔 metrics、logs、traces、errors、APM 或平台原生觀測的哪一段，再討論資料模型、查詢能力、成本與案例回寫。

## 讀法

可觀測性服務要從訊號責任進入。讀者如果要建立 metrics baseline，先回到 [Metrics Basics](/backend/04-observability/metrics-basics/)；如果要處理資料品質，先回到 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)；如果要交付 evidence，先回到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## T1 服務頁大綱

| 服務                                                                            | 類型              | 頁面要回答的核心問題                                                    |
| ------------------------------------------------------------------------------- | ----------------- | ----------------------------------------------------------------------- |
| [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)               | Standard / SDK    | instrumentation、collector、semantic convention 如何降低 vendor lock-in |
| [Prometheus](/backend/04-observability/vendors/prometheus/)                     | Metrics           | pull model、PromQL、cardinality 與 retention 如何取捨                   |
| [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)               | OSS / Cloud stack | Grafana、Loki、Tempo、Mimir 如何組成可觀測性平台                        |
| [Datadog](/backend/04-observability/vendors/datadog/)                           | SaaS APM          | all-in-one APM、logs、traces、profiling 與成本治理如何取捨              |
| [Elastic Stack](/backend/04-observability/vendors/elastic-stack/)               | Search / logs     | log search、index lifecycle、APM 與資料量成本如何治理                   |
| [Honeycomb](/backend/04-observability/vendors/honeycomb/)                       | High-cardinality  | event-based observability 與 high-cardinality 查詢如何支援除錯          |
| [AWS CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/)             | AWS-native        | AWS metrics、logs、alarms 與 account / region 邊界如何管理              |
| [GCP Cloud Operations](/backend/04-observability/vendors/gcp-cloud-operations/) | GCP-native        | Cloud Monitoring、Logging、Trace 與 GCP resource model 如何整合         |
| [Sentry](/backend/04-observability/vendors/sentry/)                             | Error tracking    | error event、release、trace、session replay 如何連到 owner action       |

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook、「← X」代表從 X 遷入、其他形式代表 same-vendor 的 topology / version / config 變動。

| Vendor                          | Deep article | Migration playbook                                                                                    |
| ------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| [Datadog](datadog/)             | —            | [← New Relic](datadog/migrate-from-new-relic/) / [→ Grafana Stack](datadog/migrate-to-grafana-stack/) |
| [Elastic Stack](elastic-stack/) | —            | [→ Elastic Cloud](elastic-stack/migrate-to-elastic-cloud/)                                            |
| [Grafana Stack](grafana-stack/) | —            | [Prometheus → Cloud Metrics](grafana-stack/migrate-prometheus-to-cloud-metrics/)                      |
| [Honeycomb](honeycomb/)         | —            | [← Sentry](honeycomb/migrate-from-sentry/)                                                            |

其他 T1 vendor（OpenTelemetry / Prometheus / AWS CloudWatch / GCP Cloud Operations / Sentry）尚未開始。對應的 backlog 議題見上方「T1 服務頁大綱」段每個服務頁要回答的核心問題、跟各 vendor `_index.md` 的「預計實作話題」段。

## 服務頁撰寫欄位

| 欄位     | 可觀測性服務頁要保留的問題                                                       |
| -------- | -------------------------------------------------------------------------------- |
| 服務責任 | 它承擔 signal standard、metrics、logs、traces、error tracking 還是 APM platform  |
| 適用壓力 | cardinality、retention、debug speed、multi-cloud、compliance、成本哪個壓力最明顯 |
| 替代邊界 | OSS stack、cloud-native、SaaS APM、specialized error tracking 的機會成本         |
| 操作成本 | instrumentation、agent、collector、index、retention、query cost、PII governance  |
| Evidence | dashboard、query link、trace sample、log sample、alert rule、data quality note   |
| 案例回寫 | 事故、capacity、release gate 與 cost attribution 如何回寫成 evidence package     |

## 服務頁標準章節

| 章節                 | 可觀測性服務頁要補的內容                                                           |
| -------------------- | ---------------------------------------------------------------------------------- |
| 服務定位             | 它是 standard、metrics backend、log search、trace backend、APM 還是 error tracking |
| 本章目標             | 讀者能判斷 signal ownership、data quality、cardinality、retention 與 cost          |
| 最短判讀路徑         | 用「現在缺哪個訊號會阻止決策」快速判斷該看 metrics、logs、traces 或 errors         |
| 日常操作與決策形狀   | instrumentation、collector、agent、dashboard、alert、retention                     |
| 核心取捨表           | OSS stack、SaaS APM、cloud-native、specialized tool 的機會成本                     |
| 進階主題             | high-cardinality、sampling、multi-cloud、PII redaction、cost attribution           |
| 排錯與失敗快速判讀   | missing signal、label explosion、trace gap、log index cost、alert noise            |
| 何時改走其他服務     | 標準化先用 OpenTelemetry、規模化 metrics 轉 managed backend、事故協作轉 08         |
| 不在本頁內的主題     | 每種語言 SDK 完整教學、dashboard 美術、所有 query cookbook                         |
| 案例回寫與下一步路由 | 回到 4.20 evidence package、9.8 performance observability、8 incident cases        |

## 跨 vendor 議題對照

橫向議題在不同 vendor 用不同 mechanism 達成。本表列同一議題在 9 個 vendor 的對應位置、確保大綱不缺漏、讀者跨 vendor 查找時有索引。

| 議題          | OTel            | Prometheus      | Grafana Stack        | Datadog         | Elastic Stack | Honeycomb       | CloudWatch      | Cloud Ops       | Sentry         |
| ------------- | --------------- | --------------- | -------------------- | --------------- | ------------- | --------------- | --------------- | --------------- | -------------- |
| 訊號類型      | 全（標準）      | metrics         | 全 stack             | 全 + Security   | logs + APM    | events / traces | 全 AWS-native   | 全 GCP-native   | errors + APM   |
| 採集模式      | SDK + Collector | Pull scrape     | mixed                | Agent push      | Beats / Agent | SDK / OTLP      | Agent / native  | Agent / native  | SDK push       |
| 查詢語言      | N/A             | PromQL          | PromQL/LogQL/TraceQL | Datadog query   | KQL / ES DSL  | Honeycomb query | Logs Insights   | Logs query      | Issue filter   |
| Cardinality   | 由 backend 決定 | 受限（series）  | Mimir / Loki 各自    | 計費 per dim    | Mapping limit | 設計目標 (high) | 計費 per metric | 計費 per metric | issue grouping |
| 部署模式      | OSS standard    | OSS self-host   | OSS / Cloud          | SaaS only       | OSS / Cloud   | SaaS only       | AWS managed     | GCP managed     | OSS / SaaS     |
| 成本模型      | 取決 backend    | self-host CapEx | self-host / Cloud    | hosts + signals | self-host     | events volume   | ingestion + API | ingestion + API | events volume  |
| 多雲 / 跨平台 | 是（標準）      | 是 (OSS)        | 是                   | 是              | 是            | 是              | AWS-only        | GCP-only        | 是             |
| OTel 相容度   | 原生            | exporter        | OTLP receiver        | OTLP ingestion  | OTLP ES 7.16+ | OTLP 原生       | ADOT            | OTLP Trace 2.0+ | OTel context   |
| 主討論案例    | C2/C3/C4/C5/C8  | C1/C6/C7        | C6/C11               | C5              | C5/C6         | C7              | C1/C8           | C3              | 待補           |

對照表的用途有三：

- 寫某 vendor 頁時、檢查橫向議題是否有對應的進階主題子段
- 讀者選型時、知道對應 mechanism 在不同 vendor 的形態
- 評估遷移風險：訊號類型 + 部署模式 + OTel 相容度三維度合併判讀

下面 8 段把對照表的每行展開、避免裸表格成為終點。

### 訊號類型

訊號類型決定 vendor 解決哪一段觀測問題。**OpenTelemetry** 是 standard、覆蓋 traces / metrics / logs；**Prometheus** 純 metrics；**Grafana Stack** 全 stack（各 backend 各司其職、Loki + Tempo + Mimir + Pyroscope）；**Datadog** 全 + Security + RUM + CI；**Elastic Stack** logs 為主 + APM；**Honeycomb** events-based（不是 metrics aggregation）；**CloudWatch / Cloud Operations** 雲原生全 stack（含 traces / profiler）；**Sentry** 專精 error tracking + 簡易 APM。

選型判讀：缺哪個訊號 → 補對應 vendor；想 turnkey 全棧 → Datadog / cloud-native；想 OSS 全棧 → Grafana Stack；error tracking 已有 → Sentry / Bugsnag 補強。

### 採集模式

採集模式影響部署複雜度跟 instrumentation 工作量。**OTel** 是 SDK + Collector 兩層；**Prometheus** 是 pull scrape（service discovery）；**Grafana Stack** 各 backend 模式不同（Loki push / Tempo OTLP / Mimir remote write）；**Datadog** Agent push；**Elastic** Beats / Logstash / Agent；**Honeycomb** SDK push 或 OTLP；**CloudWatch / Cloud Ops** 雲服務內建 + Agent；**Sentry** SDK push。

選型判讀：服務在 K8s + 想自管 → Prometheus pull + Operator；應用層 push → OTel SDK + Collector；不想配 instrumentation → Datadog / cloud-native 自動。

### 查詢語言

查詢語言差異影響 dashboard / alert 設計成本。**Prometheus PromQL**（業界 metrics query 標準）；**Grafana** 支援 PromQL（Mimir）/ LogQL（Loki）/ TraceQL（Tempo）；**Datadog** 自家 query syntax；**Elastic** KQL / Lucene / ES DSL / ES|QL；**Honeycomb** point-and-click + 簡單 query；**CloudWatch** Logs Insights syntax；**Cloud Ops** 類似但 GCP-specific；**Sentry** 是 issue filter、不算 query language。

選型判讀：跨 vendor 統一 → 學 PromQL + LogQL（Grafana 通用）；vendor-specific → 依該 vendor 學；OTel 不解決 query 問題（純 instrumentation 標準）。

### Cardinality 處理

Cardinality 是 observability 成本跟可用性的關鍵。**Prometheus** 受限（series 爆炸會 OOM）；**Datadog** custom metrics 計費 per dimension；**CloudWatch / Cloud Ops** metrics 計費 per metric；**Elastic** mapping field limit；**Honeycomb** 設計目標就是 high-cardinality（events-based）；**Grafana Stack** Mimir 多 tenant 各自 cardinality budget；**Sentry** 用 issue grouping 替代 cardinality 概念。

選型判讀：high-cardinality 是核心需求（per-user / per-request debug）→ Honeycomb；中等 cardinality + 成本敏感 → Prometheus + 設計謹慎；任意 cardinality + 計費承擔 → Datadog。

### 部署模式

部署模式決定運維責任歸屬。**OTel** 是 standard、各 backend 各自部署；**Prometheus** OSS self-host；**Grafana Stack** OSS self-host / Grafana Cloud；**Datadog / Honeycomb / Sentry** SaaS（Sentry 有 self-host OSS）；**Elastic** OSS / Elastic Cloud / OpenSearch fork；**CloudWatch / Cloud Ops** 雲原生 managed。

選型判讀：要極致控制 → self-host OSS；不想運維 → SaaS（Datadog / Honeycomb / Sentry）；已在 AWS / GCP → 雲原生 + 補強；混合模式 → OTel 抽象層 + 多 backend。

### 成本模型

成本模型差異大、容易誤判。**OTel** 本身無成本、取決下游 backend；**Prometheus** self-host CapEx（compute + storage）；**Grafana Stack** self-host CapEx 或 Grafana Cloud OpEx；**Datadog** hosts + signal 各自計費（容易堆疊）；**Elastic** self-host CapEx 或 Elastic Cloud；**Honeycomb** events volume；**CloudWatch / Cloud Ops** ingestion + API call；**Sentry** events / users / replays 計費。

選型判讀：可預期固定成本 → self-host（CapEx）；流量不穩 → SaaS（OpEx + 預警）；多訊號類型 → Datadog 容易爆、Honeycomb 計費單純；AWS / GCP-only 場景 → 雲原生通常 cheaper than 第三方 SaaS。

### 多雲 / 跨平台

多雲決定 vendor 鎖定風險。**OTel** 是抽象層、最不 lock-in；**Prometheus / Grafana Stack / Elastic / Datadog / Honeycomb / Sentry** 都支援多雲；**CloudWatch** AWS-only；**Cloud Ops** GCP-only；**Azure Monitor** Azure-only（T2 候選）。

選型判讀：多雲 → 避免 AWS / GCP-only vendor、用 Datadog / Grafana Stack / OTel + multi-backend；單一雲 → 雲原生通常成本最低；既有混合 → OTel 標準化 + 漸進遷移。

### OTel 相容度

OTel 相容度影響 vendor 切換成本。各 vendor 接受程度：

- 完全相容（drop-in）：Honeycomb / Grafana Tempo / Cloud Trace（2.0+）
- 接受但 feature 落後 vendor SDK：Datadog / CloudWatch（X-Ray 整合）/ Elastic APM
- 跟 OTel 互補但設計不同：Prometheus（exporter pattern）/ Sentry（OTel context）

選型判讀：未來想換 vendor → 從 day 1 用 OTel SDK；不換 vendor → vendor SDK 較深；多 backend dual ship → OTel 唯一可行。

## 撰寫批次

| 批次 | 服務頁                                | 撰寫目的                                                  |
| ---- | ------------------------------------- | --------------------------------------------------------- |
| O1   | OpenTelemetry / Prometheus            | 建立標準、metrics baseline 與 cardinality 判準            |
| O2   | Grafana Stack / Elastic Stack         | 建立 OSS 平台、logs / traces / retention 取捨             |
| O3   | Datadog / Honeycomb / Sentry          | 建立 SaaS APM、high-cardinality 與 error tracking 對照    |
| O4   | AWS CloudWatch / GCP Cloud Operations | 建立 cloud-native observability 與 account / project 邊界 |

## 後續候選

| 類型            | 候選服務                                              | 寫作重點                                                       |
| --------------- | ----------------------------------------------------- | -------------------------------------------------------------- |
| Enterprise APM  | New Relic、Dynatrace、Splunk Observability            | SaaS APM、enterprise workflow、成本治理                        |
| OSS / Hybrid    | SigNoz、Chronosphere、VictoriaMetrics、Thanos、Cortex | Prometheus scale、managed metrics、OpenTelemetry ingestion     |
| Tracing         | Jaeger、OpenSearch Observability                      | trace backend、OpenTelemetry-native ingestion、log correlation |
| Logs / pipeline | Fluent Bit、Fluentd、Vector、OpenSearch               | log shipping、filtering、index lifecycle、cost                 |
| Error tracking  | Bugsnag、Rollbar、Raygun                              | release health、frontend / backend error ownership             |
| Cloud-native    | Azure Monitor                                         | Azure resource model、Log Analytics、cost boundary             |

主流覆蓋檢查的重點是分開 instrumentation、metrics、logs、traces、APM 與 error tracking。OpenTelemetry 是標準入口，Prometheus / Thanos / Cortex / VictoriaMetrics 是 metrics 路線，Loki / OpenSearch / Elastic 是 logs / search 路線，Jaeger / Tempo 是 tracing 路線，Datadog / New Relic / Dynatrace / Splunk 是 SaaS APM 路線。

## 下一步路由

- 上游：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 上游：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- 跨模組：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
