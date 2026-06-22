---
title: "Grafana Stack"
date: 2026-05-01
description: "Grafana / Loki / Tempo / Mimir / Pyroscope 全棧"
weight: 3
tags: ["backend", "observability", "vendor"]
---

Grafana Stack 是 Grafana Labs 提供的 OSS observability 全棧、承擔三個責任：跨 data source 統一視覺化（Grafana）、各訊號類型專屬 backend（Loki logs / Tempo traces / Mimir metrics / Pyroscope profiles）、可自管或用 Grafana Cloud（managed）。設計取捨偏向「OSS-first + signal-specific backend + 統一查詢介面」、是 Datadog 的 OSS 替代方案。

對「需要 OSS / 自管 observability、跨 data source 統一儀表板、不想 vendor lock-in」這條路徑、Grafana Stack 是首選。

## 本章目標

讀完本章後、你應該能：

1. 部署 Grafana + Prometheus + Loki + Tempo 基本棧
2. 用 LogQL 查詢 Loki、用 TraceQL 查詢 Tempo
3. 設計 dashboard as code（Jsonnet / Terraform）
4. 評估 Mimir vs Thanos 的長期 metrics 儲存選擇
5. 評估 Grafana Cloud（managed）跟自管的取捨

## 最短路徑：5 分鐘把 Grafana Stack 跑起來

```bash
# 1. 用 docker-compose 跑起 Grafana + Prometheus + Loki
# TODO: docker-compose.yml with grafana / prometheus / loki

# 2. 在 Grafana 加 data source
# TODO: Prometheus / Loki 各自的 datasource config

# 3. 建第一個 dashboard
# TODO: 用 explorer 試 PromQL + LogQL
```

最短路徑驗證 Grafana 起來、可訪 metrics + logs。實際 production 要評估 Mimir / Tempo + Grafana Cloud 取捨。

## 日常操作與決策形狀

### Grafana 視覺化

子議題：

- Data source 配置（Prometheus / Loki / Tempo / Postgres / MySQL / Elasticsearch）
- Dashboard 設計：variable + template + panel
- Dashboard as code：Jsonnet (Grafonnet) / Terraform Grafana provider
- 對應指令：HTTP API `/api/dashboards`

### LogQL（Loki 查詢）

子議題：

- LogQL syntax：log stream selector + filter + parser + aggregation
- 跟 PromQL 對齊的設計（同樣 label-based）
- 範例：`{job="app"} |= "error" | json | line_format "..."`
- 對應 metrics-from-logs（unwrap + rate）

### TraceQL（Tempo 查詢）

子議題：

- TraceQL syntax：span selector + attribute + aggregation
- 範例：`{ span.http.status_code = 500 && duration > 1s }`
- Service graph：跨服務依賴自動分析
- 對應 trace-to-logs / trace-to-metrics 關聯查詢

## Deep Article

- [LGTM Stack 組合運維](lgtm-stack-operations/)：四個元件的責任分工、部署模式、常見故障與 dashboard provisioning

## 進階主題（按需閱讀）

### Loki 設計與限制

子議題：

- Storage：S3 / GCS / 本地、按 stream 切 chunks
- Label cardinality 跟 Prometheus 一樣敏感（不是 stream content）
- LogQL 不適合 high-cardinality content search（用 Elastic）
- 對應 [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)

### Tempo trace 採集

子議題：

- 接受 OTLP / Jaeger / Zipkin protocol
- Storage：S3 / GCS、cheap object storage
- Trace ID lookup 為主、no full-text search（用 traces metrics 反向查）
- 對應 [4.C4 X-Ray to OTel](/backend/04-observability/cases/xray-to-opentelemetry-migration/)

### Mimir 長期 metrics 儲存

子議題：

- Prometheus remote write 接收 metric
- Horizontally scalable（multi-tenant）
- 跟 Thanos / Cortex 的對照（Mimir 是 Cortex fork + improvements）
- 對應 [4.C8 Airbnb K8s scale](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)

### Pyroscope continuous profiling

子議題：

- CPU / memory / mutex / goroutine profiling
- Flame graph 視覺化
- 跟 Tempo trace 關聯（trace-to-profile）
- OSS（Grafana 收購）vs Pyroscope OG

### Grafana Cloud（managed）

子議題：

- Free tier 額度 + paid tier
- 含所有 stack（Metrics / Logs / Traces / Profiles）
- Grafana Cloud vs Datadog cost 對照
- Hybrid 模式：self-host backend + Grafana Cloud Grafana

### Unified Alerting

子議題：

- Grafana 9+ 統一 alerting（取代 dashboard alert + Prometheus alertmanager 分裂）
- 跨 data source 寫 alert rule
- Multi-dimensional alert（per-label）
- 對應 Alertmanager 兼容

## 排錯快速判讀

### Dashboard 載入慢

操作原則：先看 query 範圍跟 panel 數、用 query inspector 看 query 時間分布。

### Loki query 過慢 / 失敗

操作原則：Loki query 需要 label filter 先縮範圍、再 content match。

```bash
# TODO: LogQL: {namespace="prod", app="api"} |= "error"（先 label 後 filter）
```

### Tempo span gap

操作原則：trace 不完整、看 sampling 設定 + Collector buffer 是否 drop。

### Mimir ingestion 失敗

操作原則：remote_write rate / size limit 撞到 Mimir quota。判讀：Mimir HTTP 429 / 413。

### Grafana 跟 Prometheus disconnected

操作原則：data source 連不上、看 Grafana log + network。

## 何時改走其他服務

| 需求形狀                  | 改走                                                                                                                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Pure metrics              | [Prometheus](/backend/04-observability/vendors/prometheus/) 單獨用                                                                     |
| SaaS turnkey APM          | [Datadog](/backend/04-observability/vendors/datadog/)                                                                                  |
| Log full-text search 為主 | [Elastic Stack](/backend/04-observability/vendors/elastic-stack/)                                                                      |
| High-cardinality debug    | [Honeycomb](/backend/04-observability/vendors/honeycomb/)                                                                              |
| AWS / GCP native          | [CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) / [Cloud Ops](/backend/04-observability/vendors/gcp-cloud-operations/) |
| Error tracking            | [Sentry](/backend/04-observability/vendors/sentry/)                                                                                    |
| Profile only              | Pyroscope OSS / Polar Signals                                                                                                          |

## 不在本頁內的主題

- 各 Grafana plugin 細節
- Dashboard 美術 / UX 建議
- Grafana / Loki / Tempo / Mimir 各自完整 admin 手冊
- Grafana 商業版 (Enterprise) 功能

## 案例回寫

### 直接相關案例

| 案例                                                                                                          | 主討論議題                                     |
| ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [4.C2 Gaming peak cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/) | Loki / Mimir 高峰下的 ingestion lag 與標籤治理 |
| [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)    | Loki retention / compliance                    |
| [4.C8 Airbnb K8s scale](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)              | Mimir scale / Prometheus 長期儲存              |

### 跨 vendor 對照

| 案例                                                                                            | 對 Grafana Stack 的對應                                               |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [4.C4 X-Ray to OTel](/backend/04-observability/cases/xray-to-opentelemetry-migration/)          | 從 X-Ray 遷出後 Tempo 是 OSS trace backend 候選                       |
| [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/) | 從 Datadog 遷出可去 Grafana Cloud                                     |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)      | 小型 single Grafana / 中型加 Loki+Tempo / 大型 Grafana Cloud 或 Mimir |

## 下一步路由

- 上游概念：[Metrics Basics](/backend/04-observability/metrics-basics/)
- 平行 vendor：[Prometheus](/backend/04-observability/vendors/prometheus/)、[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
