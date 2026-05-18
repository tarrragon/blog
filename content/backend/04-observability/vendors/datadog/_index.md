---
title: "Datadog"
date: 2026-05-01
description: "All-in-one SaaS 觀測平台、APM / Logs / Metrics / RUM / Security"
weight: 4
tags: ["backend", "observability", "vendor"]
---

Datadog 是 all-in-one SaaS observability 平台、承擔三個責任：覆蓋 APM / logs / metrics / RUM / synthetics / security / CI visibility 全訊號類型、auto-instrumentation 廣度業界第一、跟 600+ integrations 即插即用。設計取捨偏向「turnkey + 廣度 + integration」、成本是主要取捨點。

對「想要 turnkey 體驗、不想自管 observability、多訊號類型統一平台、團隊規模可承擔成本」這條路徑、Datadog 是首選。

## 本章目標

讀完本章後、你應該能：

1. 安裝 Datadog Agent、配置 APM auto-instrumentation
2. 用 Datadog Logs / Metrics / APM 三大查詢介面
3. 控制 cost（log indexing / metric cardinality / APM trace sampling）
4. 寫 Monitor as code（Terraform）
5. 評估 OTLP ingestion 跟 Datadog SDK 的取捨

## 最短路徑：5 分鐘把 Datadog 跑起來

```bash
# 1. 安裝 Agent
# TODO: DD_API_KEY=<key> DD_SITE="datadoghq.com" bash -c "$(curl -L ...)"

# 2. 啟用 APM
# TODO: 在 Agent config 加 apm_config.enabled: true
# TODO: 應用程式加 ddtrace-run / dd-trace-py

# 3. 驗證 Agent + APM 上線
# TODO: 在 Datadog UI 看 Host map + APM Service List
```

## 日常操作與決策形狀

### Agent 安裝與配置

子議題：

- 安裝方式：package（apt/yum）/ container / K8s DaemonSet / Lambda extension
- Agent config：core / APM / Logs / NetFlow / SNMP 各 sub-config
- DogStatsD：應用層 custom metrics 入口
- 對應指令：`datadog-agent status`、`/etc/datadog-agent/datadog.yaml`

### APM 自動 instrumentation

子議題：

- 各語言 tracer：dd-trace-java / dd-trace-py / dd-trace-js / dd-trace-go
- Auto-instrumentation 廣度（業界最廣）
- Service / Resource / Operation 三層 trace 結構
- 對應 [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)

### Logs 配置

子議題：

- 採集方式：Agent 採集 / Fluent Bit / Vector → Datadog
- Indexing vs Archives：indexing 費錢但可查、archives 便宜但只能 rehydrate
- Log Pipeline：parsing / enrichment / sensitive data scrubbing
- 對應 cost 控制：indexing rate / retention

### Metrics

子議題:

- Custom metrics（DogStatsD / Agent / API）
- Metric Type：count / gauge / histogram / distribution
- Cardinality 控制：每 metric 收 tags 數限制
- 對應 [4.C2 Gaming cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)

## 進階主題（按需閱讀）

### 成本治理

子議題：

- Hosts pricing（vs APM / Logs / Custom Metrics 各自獨立）
- Log indexing rate 控制（Exclusion Filters）
- Custom metrics 計費（per metric per host）
- APM trace sampling
- 對應 Datadog Usage Attribution

### OTLP ingestion

子議題：

- Datadog Agent 接受 OTLP（gRPC + HTTP）
- 對 OTel SDK 用戶的優勢（avoid Datadog SDK lock-in）
- 對應 [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)
- Datadog 自家 SDK vs OTel：feature parity 取捨

### Monitor as code

子議題：

- Terraform Datadog provider：dashboard / monitor / SLO / synthetic
- 跟 IaC pipeline 整合
- 多環境（dev / staging / prod）配置

### APM Trace Sampling

子議題：

- Head-based sampling（rate-based）
- Tail-based（Datadog 新功能、需 Agent 支援）
- Ingestion vs Indexing sampling 兩層
- 對應 cost 控制

### RUM / Synthetics

子議題：

- RUM（Real User Monitoring）：前端用戶體驗
- Synthetics：browser test / API test 主動探測
- Session Replay
- 跟 APM 關聯：frontend trace → backend trace

### Security Monitoring

子議題：

- Cloud SIEM
- ASM（Application Security Management、wAF/RASP）
- Cloud Security Posture Management
- 跟 [07 security 模組](/backend/07-security-data-protection/) 對照

## 排錯快速判讀

### Agent 連不上 Datadog

操作原則：先 `datadog-agent status` 看 connectivity、再看 API key + region。

### APM trace 缺失

操作原則：trace context propagation 在跨 service / 跨 thread 邊界丟失。

```bash
# TODO: dd-trace-py debug mode / `DD_TRACE_DEBUG=true`
```

### Log indexing cost 爆

操作原則：indexed log 量超預期、用 Exclusion Filter 過濾不必要 log。判讀：Datadog Usage page 看每 day indexed log。

### Custom metrics 爆預算

操作原則：每 host 每 metric 計費、cardinality 高（per-user / per-request label）會爆。判讀：Metrics Summary 看 metric volume。

### Monitor noise

操作原則：alert 太多、低品質、用 Composite Monitor + Recovery / No data threshold。

## 何時改走其他服務

| 需求形狀                    | 改走                                                                                                                            |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 預算敏感                    | [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（OSS）/ Cloud（cheaper）                                      |
| 需要 OSS / self-host        | [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) + [Prometheus](/backend/04-observability/vendors/prometheus/) |
| High-cardinality debug 深度 | [Honeycomb](/backend/04-observability/vendors/honeycomb/)                                                                       |
| AWS-only + 成本             | [CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/)                                                                 |
| 純 error tracking           | [Sentry](/backend/04-observability/vendors/sentry/)                                                                             |
| 多 vendor 標準化            | [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/) + 任一 backend                                                |
| Logs full-text 為主         | [Elastic](/backend/04-observability/vendors/elastic-stack/)                                                                     |

## 不在本頁內的主題

- 各語言 dd-trace SDK 完整 API
- Datadog UI 操作詳細
- Pricing 詳細計算（用 Datadog Usage page）
- 600+ integrations 各自設定

## 案例回寫

### 直接相關案例

| 案例                                                                                            | 主討論議題                |
| ----------------------------------------------------------------------------------------------- | ------------------------- |
| [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/) | OTLP ingestion + SDK 移轉 |

### 跨 vendor 對照

| 案例                                                                                                     | 對 Datadog 的對應                               |
| -------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [4.C1 Fintech audit](/backend/04-observability/cases/fintech-audit-evidence-observability/)              | Datadog Logs Indexing / Archives 作為審計證據面 |
| [4.C2 Gaming cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/) | Custom metrics cardinality 治理                 |
| [4.C9 OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/) | （反例）Datadog SDK ↔ OTLP 雙軌語意漂移         |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)               | 中大型常選 Datadog turnkey                      |

**待補 Datadog 案例**：客戶 cost optimization stories、large scale 部署（Shopify / Coinbase / Zoom 等）engineering blog。

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)、[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
