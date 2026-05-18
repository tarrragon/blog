---
title: "GCP Cloud Operations"
date: 2026-05-01
description: "GCP 原生觀測性套件（前 Stackdriver）：Logging / Monitoring / Trace / Profiler"
weight: 8
tags: ["backend", "observability", "vendor"]
---

GCP Cloud Operations（前 Stackdriver）是 GCP 原生 observability 套件、承擔三個責任：GCP 服務內建 Cloud Logging / Monitoring / Trace（無需配置）、跟 GCP 資源 model 深度整合（project / folder / org）、BigQuery 匯出長期 logs 跟分析。設計取捨偏向「GCP 生態 turnkey + BigQuery 整合 + Cloud Profiler 持續 profiling」、跨雲跟進階 distributed tracing 是限制。

## 本章目標

讀完本章後、你應該能：

1. 用 gcloud / Console 查 Cloud Logging / Monitoring
2. 設計 structured logging + log-based metrics
3. 用 Cloud Monitoring uptime checks + SLO + alerting policy
4. 用 Cloud Trace + Cloud Profiler 做 application performance
5. 配置 BigQuery 匯出長期 logs 跟分析

## 最短路徑：5 分鐘把 Cloud Operations 跑起來

```bash
# 1. GCP 預設啟用 Cloud Logging / Monitoring（free tier 額度）
# TODO: GKE / Cloud Run / Cloud Functions 自動 log + metric

# 2. 查詢 logs
# TODO: gcloud logging read 'resource.type="gae_app" AND severity>=ERROR'

# 3. 用 Logs Explorer 視覺化查詢
# TODO: Console → Logging → Logs Explorer
```

## 日常操作與決策形狀

### Cloud Logging 結構化 logs

子議題：

- jsonPayload：結構化 log（推薦）
- Severity 7 級（DEBUG / INFO / NOTICE / WARNING / ERROR / CRITICAL / ALERT）
- Resource type / Resource labels：自動帶入
- 對應 [4.C3 Cloud Trace OTLP](/backend/04-observability/cases/cloud-trace-otlp-adoption/)

### Log-based metrics

子議題：

- Counter metric：log 出現次數
- Distribution metric：log field 數值分布
- 適合：把 application log 轉成 metric trigger alert
- 對應指令：`gcloud logging metrics create`

### Cloud Monitoring uptime checks / SLO

子議題：

- Uptime check：HTTP / HTTPS / TCP / ICMP 多地點 probe
- SLO：service indicator + objective + window + burn rate alert
- Multi-window SLO alert（類 Honeycomb burn rate）
- 對應 [knowledge cards burn-rate](/backend/knowledge-cards/burn-rate/)

### Cloud Trace

子議題：

- 接受 OTLP（Cloud Trace 2.0+）
- 自動採集 GCP service（Cloud Run / GKE / App Engine）
- 對應 [4.C3 Cloud Trace OTLP adoption](/backend/04-observability/cases/cloud-trace-otlp-adoption/)
- 跟 X-Ray 比、distributed tracing 較基礎

## 進階主題（按需閱讀）

### Cloud Profiler

子議題：

- 持續 profiling（CPU / Heap / Wall time / Mutex）
- 支援 Go / Java / Python / Node
- Flame graph 視覺化
- 跟 Pyroscope / Datadog Profiler 對照

### BigQuery 匯出長期儲存

子議題：

- Log Router：定義 sink 把 logs 匯出 BigQuery / GCS / Pub/Sub
- BigQuery 適合長期 + 分析查詢（SQL）
- 對應 [4.C6 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)
- Cost：BigQuery storage 比 Cloud Logging cheaper

### Error Reporting

子議題：

- 自動聚合 application error
- 各語言 client library（Python / Java / Node / Go）
- 跟 Sentry 對照（Sentry 更深 / 更廣）

### Cloud Monitoring agent

子議題：

- Ops Agent（取代 Stackdriver agent）：統一 logs + metrics 採集
- 支援 GCE / Bare metal / AWS / on-prem
- 配置：YAML config + receivers / processors / exporters（類 OTel Collector）

### Multi-project / Multi-region 治理

子議題：

- Aggregated logging sink：跨 project 集中 logs
- Cross-project SLO
- Workspace（前 Stackdriver workspace）已 deprecated、改用 Metrics Scope

### OTLP integration

子議題：

- Cloud Trace 接受 OTLP（2024 GA）
- Cloud Monitoring 接受 OTel metrics（via OTel Collector + GCP exporter）
- Logs in OTel 跟 Cloud Logging 整合（成熟中）
- 對應 [4.C3 Cloud Trace OTLP](/backend/04-observability/cases/cloud-trace-otlp-adoption/)

## 排錯快速判讀

### Logs 沒出現

操作原則：先看 resource type / project 是否對、再看 IAM 權限。

```bash
# TODO: gcloud logging read --project=<id> --resource-type=...
```

### Monitoring 查不到 metric

操作原則：metric name + project + filter 是否對。對應 Metrics Explorer 確認 metric 存在。

### SLO alert noise

操作原則：multi-window burn rate 設計避免噪音。

### Cloud Trace 太空

操作原則：sampling 不足或 SDK 沒配置。判讀：Cloud Trace 看 span count + 確認 SDK Cloud Trace exporter 設定。

### BigQuery 匯出 cost 爆

操作原則：sink filter 沒收斂、所有 logs 都匯。判讀：Cloud Logging usage 看 export volume。

## 何時改走其他服務

| 需求形狀               | 改走                                                                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 多雲統一觀測           | [Datadog](/backend/04-observability/vendors/datadog/) / [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) / [OTel](/backend/04-observability/vendors/opentelemetry/) |
| 進階 APM 廣度          | [Datadog](/backend/04-observability/vendors/datadog/)                                                                                                                                |
| High-cardinality debug | [Honeycomb](/backend/04-observability/vendors/honeycomb/)                                                                                                                            |
| Logs full-text 進階    | [Elastic](/backend/04-observability/vendors/elastic-stack/) / Loki                                                                                                                   |
| AWS / Azure 生態       | [CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) / Azure Monitor                                                                                                      |
| Error tracking 進階    | [Sentry](/backend/04-observability/vendors/sentry/)                                                                                                                                  |

## 不在本頁內的主題

- gcloud / Cloud Console UI 操作詳細
- 各 GCP 服務的內建 metric 完整列表
- Cloud Trace span structure 細節
- BigQuery SQL syntax

## 案例回寫

### 直接相關案例

| 案例                                                                                | 主討論議題             |
| ----------------------------------------------------------------------------------- | ---------------------- |
| [4.C3 Cloud Trace OTLP](/backend/04-observability/cases/cloud-trace-otlp-adoption/) | OTLP 在 GCP 的採用路徑 |

### 跨 vendor 對照

| 案例                                                                                                       | 對 Cloud Operations 的對應         |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| [4.C6 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/) | BigQuery 匯出長期 retention        |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)                 | GCP-only 場景優先 Cloud Operations |

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)、[CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/)
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
