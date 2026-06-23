---
title: "Datadog OTLP Ingestion 與 OTel 整合"
date: 2026-06-23
description: "說明 Datadog Agent 的 OTLP receiver 配置、OTel SDK 與 Datadog SDK 的 feature parity 差異、resource attribute mapping、常見故障與成本模型"
weight: 11
tags: ["backend", "observability", "datadog", "opentelemetry", "otlp"]
---

> 本文是 [Datadog](/backend/04-observability/vendors/datadog/) 的 vendor deep article，深化 overview「OTLP ingestion」段。初次接觸 Datadog 的讀者建議先讀 [Datadog 服務頁](/backend/04-observability/vendors/datadog/)。

## 問題情境

兩種觸發情境會讓團隊需要 Datadog 的 OTLP ingestion：

團隊已經使用 Datadog APM，但新服務或新語言想用 OTel SDK 避免 vendor lock-in。Datadog SDK 覆蓋的語言有限（Go / Java / Python / Ruby / Node / .NET / PHP / C++），如果服務用 Rust / Elixir / Kotlin multiplatform，OTel SDK 的覆蓋更廣。

另一種情境是團隊原本用 OTel + Jaeger 或 OTel + Grafana，現在想把 visualization 遷到 Datadog 但不想重新 instrument。OTLP ingestion 讓 OTel SDK 產出的 traces / metrics / logs 直接送進 Datadog，不改 application code。

## 核心概念

### Datadog Agent 的 OTLP receiver

Datadog Agent 6.32+ 內建 OTLP receiver，接受 gRPC（port 4317）和 HTTP（port 4318）兩種 protocol。Agent 收到 OTLP 資料後轉換成 Datadog 內部格式，走跟 Datadog SDK 相同的 pipeline（sampling、tagging、forwarding to Datadog backend）。

這代表 OTLP path 的資料在 Datadog UI 裡跟 Datadog SDK path 的資料一樣被處理 — 相同的 APM trace waterfall、相同的 service map、相同的 error tracking。差異在 metadata 完整度（見下方 feature parity）。

### 三種 signal 的 OTLP 支援度

| Signal  | OTLP 支援                          | 到 Datadog 的對應                        |
| ------- | ---------------------------------- | ---------------------------------------- |
| Traces  | 完整（OTLP gRPC / HTTP）           | APM traces、service map、error tracking  |
| Metrics | 完整（OTLP gRPC / HTTP）           | Custom metrics（按 metric 計費）         |
| Logs    | 有限（Agent 7.54+ 支援 OTLP logs） | Datadog Logs（按 ingestion volume 計費） |

Traces 的 OTLP 支援最成熟、metrics 次之、logs 最新。混合環境常見做法是 traces + metrics 走 OTLP、logs 走 Datadog Agent 的原生 log collection（file tailing / container stdout）。

### Datadog SDK vs OTel SDK feature parity

| 功能                                 | Datadog SDK                                    | OTel SDK → Datadog                      |
| ------------------------------------ | ---------------------------------------------- | --------------------------------------- |
| Distributed tracing                  | 有                                             | 有（完整）                              |
| Continuous profiling                 | 有                                             | 無（Datadog 專有）                      |
| ASM（Application Security）          | 有                                             | 無（需要 Datadog library）              |
| CI Visibility                        | 有                                             | 無                                      |
| Dynamic instrumentation              | 有                                             | 無                                      |
| Runtime metrics（GC、thread）        | 自動                                           | 需手動配置 OTel metric instrumentation  |
| Log correlation（trace_id 注入 log） | 自動                                           | 需手動配置（MDC / context propagation） |
| Unified service tagging              | 自動（`DD_SERVICE` / `DD_ENV` / `DD_VERSION`） | 需 resource attribute mapping           |

判讀：如果團隊需要 profiling / ASM / CI Visibility，對應服務仍需 Datadog SDK。其他服務可以用 OTel SDK + OTLP ingestion，兩者在同一個 Datadog org 共存。

## 配置 step-by-step

### Datadog Agent OTLP 設定

```yaml
# datadog.yaml
otlp_config:
  receiver:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
```

Agent 重啟後用 `datadog-agent status` 確認 OTLP receiver 啟動。

### OTel SDK endpoint 配置

```bash
# 環境變數（語言無關）
export OTEL_EXPORTER_OTLP_ENDPOINT="http://datadog-agent:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_SERVICE_NAME="checkout-api"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production,service.version=1.2.3"
```

### Resource attribute → Datadog tag mapping

Datadog Agent 自動把 OTel resource attributes 轉成 Datadog tags：

| OTel resource attribute  | Datadog tag      | 備註                                   |
| ------------------------ | ---------------- | -------------------------------------- |
| `service.name`           | `service`        | Datadog unified service tagging 的核心 |
| `deployment.environment` | `env`            | 必填、否則 Datadog UI 的環境篩選失效   |
| `service.version`        | `version`        | 用於 deployment tracking               |
| `host.name`              | `host`           | Agent 通常自動帶、不需手動設           |
| `container.name`         | `container_name` | K8s 環境自動帶                         |

如果 resource attribute 沒設 `deployment.environment`，Datadog 會把 trace 歸到 `env:none` — 在 APM 介面幾乎不可見。這是最常見的 OTLP onboarding 問題。

### OTel Collector → Datadog（alternative path）

如果不想讓 application 直連 Datadog Agent，可以在中間放 OTel Collector：

```yaml
# otel-collector-config.yaml
exporters:
  datadog:
    api:
      key: ${DD_API_KEY}
      site: datadoghq.com

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [datadog]
```

OTel Collector 的 `datadog` exporter 直接把資料送到 Datadog backend（不經 Agent）。適合已有 OTel Collector 基礎設施、不想每個 node 都部署 Datadog Agent 的場景。

## 故障與邊界

### Resource attribute mapping 不對齊

OTel 的 `service.name` 用 dot notation（如 `com.example.checkout`），Datadog 預設用 hyphen（如 `checkout-api`）。如果 mapping 不一致，同一個服務在 Datadog APM 的 service map 會出現多個節點（OTel path 一個、Datadog SDK path 一個）。

修法：統一 `service.name` 命名。如果兩種 SDK 並存，在 OTel SDK 的 resource attribute 設跟 Datadog SDK 的 `DD_SERVICE` 完全相同的值。

### Metric naming convention 差異

OTel metric 用 dot notation（`http.server.request.duration`），Datadog 預設用 underscore（`http_server_request_duration`）。Agent 會自動轉換（dot → underscore），但如果團隊同時有 Datadog SDK 產出的 metric 跟 OTel SDK 產出的 metric，兩者可能在 Datadog 裡產生重複（語意相同但名稱不同）。

修法：用 OTel Collector 的 `metricstransform` processor 在 export 前統一命名，或在 Datadog 用 metric alias 合併。

### Log correlation 在 OTLP path 的限制

Datadog SDK 自動把 `dd.trace_id` 和 `dd.span_id` 注入 application log（如 Python logging、Java MDC）。OTel SDK 不做這件事 — log correlation 需要手動設定（把 `trace_id` 從 OTel context 注入 logging framework）。

如果 log correlation 缺失，Datadog 的 trace → log 跳轉功能失效。修法依語言不同：Java 用 MDC + OTel Java agent 的 log context instrumentation；Python 用 `opentelemetry-instrumentation-logging`；Go 需要手動從 span context 取 trace ID 寫到 log field。

## 容量與成本

OTLP path 的計費跟 Datadog SDK path 相同：

| Signal     | 計費單位                                                  | OTLP vs Datadog SDK |
| ---------- | --------------------------------------------------------- | ------------------- |
| APM traces | Per ingested span                                         | 相同                |
| Metrics    | Per custom metric（unique metric name × tag combination） | 相同                |
| Logs       | Per ingested GB                                           | 相同                |

成本差異不在 ingestion pricing，在 **feature access**。用 OTel SDK 失去 Profiling / ASM / CI Visibility，這些功能需要 Datadog SDK。如果團隊需要這些功能，走 OTLP 反而要為核心服務額外部署 Datadog SDK — 雙 SDK 的 maintenance cost 可能超過直接全用 Datadog SDK。

判斷分水嶺：如果 > 80% 的服務不需要 Profiling / ASM，走 OTLP + 少數服務用 Datadog SDK 是合理的混合模式。如果核心服務都需要 Profiling，全用 Datadog SDK 更簡單。

## 整合與下一步

- [Datadog 服務頁](/backend/04-observability/vendors/datadog/)：overview 與日常操作
- [Datadog 成本治理](../cost-governance-agent-config/)：Agent 配置與 cost control
- [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)：從 Datadog SDK 轉向 OTel 相容模式的治理案例
- [OpenTelemetry Collector 部署模式](/backend/04-observability/vendors/opentelemetry/collector-deployment-patterns/)：OTel Collector → Datadog 的 alternative path
- [← New Relic migration](../migrate-from-new-relic/)：New Relic → Datadog 的遷移中 OTLP 扮演的橋接角色
