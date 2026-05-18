---
title: "OpenTelemetry"
date: 2026-05-01
description: "可觀測性開放標準、SDK 與 Collector"
weight: 1
tags: ["backend", "observability", "vendor"]
---

OpenTelemetry（OTel）是 CNCF 開放標準、承擔三個責任：定義 traces / metrics / logs 的資料模型（spec）、提供 vendor-neutral 的 SDK 跟 auto-instrumentation、以 OTel Collector 作為 instrumentation 跟 backend 之間的抽象層。設計取捨偏向「抽象優於 vendor-specific feature」、避免 vendor lock-in 是核心動機。多數現代 observability 平台（Datadog / Honeycomb / Grafana Cloud / Cloud Operations）都接受 OTLP。

本頁先給最短路徑、再展開日常 instrumentation 跟 Collector 部署、最後進階治理（sampling / semantic conventions / logs 成熟度）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 OTel SDK 或 auto-instrumentation 對應用程式做 instrumentation
2. 配置 OTLP exporter 把 telemetry 送到任一 backend
3. 部署 OTel Collector（agent / gateway 模式）作為 backend 切換抽象層
4. 區分 head-based vs tail-based sampling、選擇對應策略
5. 評估從 vendor SDK 遷移到 OTel SDK 的相容性風險

## 最短路徑：5 分鐘把 OTel 跑起來

```bash
# 1. 應用程式加 auto-instrumentation（範例：Python）
# TODO: opentelemetry-bootstrap -a install
# TODO: opentelemetry-instrument --traces_exporter otlp --metrics_exporter otlp python app.py

# 2. 啟動 OTel Collector
# TODO: docker run -p 4317:4317 -p 4318:4318 otel/opentelemetry-collector-contrib

# 3. Collector 配置範例
# TODO: otel-collector-config.yaml with otlp receiver + exporter to backend
```

最短路徑驗證 telemetry 從 app → Collector → backend 串通。實際 production 要評估 sampling、retention、cardinality。

## 日常操作與決策形狀

### Instrumentation 模式

子議題：

- Auto-instrumentation：Java / Python / Node / .NET / Ruby / Go 各語言成熟度不同
- Manual instrumentation：開發者寫 trace span / metric instrument
- Library instrumentation：opentelemetry-instrumentation-<lib>（HTTP client / DB / framework）

### OTLP exporter 配置

子議題：

- OTLP gRPC（4317）vs HTTP（4318）
- Endpoint / headers / authentication 配置
- 對應指令範例：環境變數 `OTEL_EXPORTER_OTLP_ENDPOINT`、`OTEL_EXPORTER_OTLP_HEADERS`

### Collector 部署模式

子議題：

- **Agent**：跟應用程式同 host / pod、做 local buffer + enrichment
- **Gateway**：集中部署、跨多 agent 接收、做 sampling / routing
- **Sidecar**：K8s sidecar pattern、跟 pod 同生命週期
- 對應配置：receivers / processors / exporters pipeline

## 進階主題（按需閱讀）

### Auto-instrumentation 跨語言成熟度

子議題：

- Java：最成熟、auto-instrumentation 廣度最大
- Python：成熟、覆蓋主流 framework
- Node：成熟、async context propagation 較複雜
- Go：較弱（runtime 不支援 monkey patching）、多用 manual
- .NET：成熟、跟 Application Insights 對齊
- Ruby / PHP：相對較弱、覆蓋主流 framework

### Sampling 策略

對應案例 [4.C5 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)。子議題：

- **Head-based sampling**：trace 開始時決定保留與否、低成本但 lose context
- **Tail-based sampling**：trace 完成後決定（依錯誤 / 延遲）、Collector 要 buffer 整個 trace
- Sampling rate 配置（global / per-service / probabilistic）
- 對應工具：OTel Collector 的 tail_sampling processor、Refinery（Honeycomb）

### Semantic conventions

子議題：

- HTTP / DB / messaging / RPC 等的 attribute 命名規範
- Resource attributes（service.name / service.version / deployment.environment）
- Span name / status code convention
- Migration：應用層用 OTel semantic conventions、避免 vendor-specific naming

### Logs in OTel

子議題：

- Logs 比 metrics / traces 較晚進 OTel spec（v1.0 較新）
- Log signal 設計：log record 跟 span 關聯（trace_id / span_id）
- 跟 Loki / Elastic / CloudWatch 的整合
- 從現有 logging library 移轉的路徑（log-forwarding vs SDK）

### Vendor SDK vs OTel SDK 遷移

對應案例 [4.C8 X-Ray to OpenTelemetry](/backend/04-observability/cases/xray-to-opentelemetry-migration/) 與 [4.C5 Datadog OTel](/backend/04-observability/cases/datadog-otel-migration-practice/)。子議題：

- 動機：避免 vendor lock-in、多 backend 並存、開源治理
- 風險：vendor-specific feature 損失（profiling / RUM 整合）
- 遷移路徑：dual ship → cutover → cleanup
- 對應 [4.C9 反例：OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/)

### Resource detection

子議題：

- 自動偵測 cloud provider（AWS / GCP / Azure）resource attributes
- K8s resource detector（pod / namespace / cluster）
- Container resource detector
- 對應配置：`OTEL_RESOURCE_ATTRIBUTES`

## 排錯快速判讀

### Telemetry 沒到 backend

操作原則：先確認 SDK 配置正確、再看 Collector 是否收到、最後看 exporter 是否成功。

```bash
# TODO: 設 OTEL_LOG_LEVEL=debug 看 SDK 內部 log
# TODO: 看 Collector internal metrics（zPages / Prometheus exporter）
```

判讀路徑：SDK → Collector → backend、三段各自獨立、要逐層 isolate。

### Cardinality explosion

操作原則：metric attribute 含 high-cardinality 值（user_id / session_id）會爆 backend 成本。判讀：看 backend 的 series 數量、找 attribute 來源。

### Trace span gap

操作原則：trace 不完整、看 context propagation 是否在跨 service / 跨 thread 邊界丟失。

### Auto-instrumentation 不生效

操作原則：確認 SDK 版本跟 library version 對應、agent 啟動方式正確。對應 [4.C2 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/) 的踩坑經驗。

### Sampling 過頭 / 不足

操作原則：sampling rate 跟 backend 預算 + debug 需求對齊。判讀：debug 時找不到 trace（sampling 過頭）vs backend 成本爆（sampling 不足）。

## 何時改走其他服務

| 需求形狀                    | 改走                                                                        |
| --------------------------- | --------------------------------------------------------------------------- |
| 需要 metrics 後端           | [Prometheus](/backend/04-observability/vendors/prometheus/) / Mimir         |
| 需要 SaaS APM 整合          | [Datadog](/backend/04-observability/vendors/datadog/) / New Relic           |
| 需要 logs 後端              | [Elastic Stack](/backend/04-observability/vendors/elastic-stack/) / Loki    |
| 需要 high-cardinality debug | [Honeycomb](/backend/04-observability/vendors/honeycomb/)                   |
| AWS-native                  | [CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) + X-Ray     |
| GCP-native                  | [Cloud Operations](/backend/04-observability/vendors/gcp-cloud-operations/) |
| Error tracking              | [Sentry](/backend/04-observability/vendors/sentry/)                         |

## 不在本頁內的主題

- 各語言 SDK 完整 API
- OTLP protocol binary format
- 各 backend 的 OTel 整合細節（見各 backend vendor 頁）
- OTel project governance / sig 細節

## 案例回寫

### 直接相關案例

| 案例                                                                                                 | 主討論議題                       |
| ---------------------------------------------------------------------------------------------------- | -------------------------------- |
| [4.C2 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)      | OTLP ingestion / vendor SDK 移轉 |
| [4.C3 Cloud Trace OTLP](/backend/04-observability/cases/cloud-trace-otlp-adoption/)                  | GCP Cloud Trace 接受 OTLP        |
| [4.C4 ADOT EKS pipeline](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/) | AWS Distro for OTel + EKS        |
| [4.C8 X-Ray to OTel](/backend/04-observability/cases/xray-to-opentelemetry-migration/)               | 從 vendor SDK 遷出 OTel          |

### 跨 vendor 對照

| 案例                                                                                                     | 對 OTel 的對應                                       |
| -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [4.C9 OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/) | （反例）遷移期間 signal 不一致                       |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)               | 小型直接 SDK / 中型加 Collector / 大型 multi-backend |

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：所有 04 vendor 都可作 OTel backend
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
