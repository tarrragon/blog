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
