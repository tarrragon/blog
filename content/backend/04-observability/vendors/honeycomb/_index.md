---
title: "Honeycomb"
date: 2026-05-01
description: "High-cardinality observability 平台、events-based 模型"
weight: 6
tags: ["backend", "observability", "vendor"]
---

Honeycomb 是 high-cardinality observability SaaS、承擔三個責任：events-based 資料模型（不是 metrics aggregation）、unknown-unknowns 偵錯能力（BubbleUp / Heatmap）、observability-driven SRE 文化代表平台。設計取捨偏向「深度優於廣度」、不追求 Datadog 的 integration 廣度、專注於 high-cardinality + distributed system debugging。

## 本章目標

讀完本章後、你應該能：

1. 用 Honeycomb SDK 或 OTel 送 events 到 Honeycomb
2. 用 BubbleUp 找 outlier 模式（unknown-unknowns）
3. 設計 SLO + burn rate alert
4. 配置 Refinery（tail-based sampling）
5. 評估 Honeycomb vs Datadog 的選用判讀

## 最短路徑：5 分鐘把 Honeycomb 跑起來

```bash
# 1. 應用程式加 instrumentation（Honeycomb SDK 或 OTel SDK）
# TODO: HONEYCOMB_API_KEY + dataset 設定
# TODO: 用 Beeline SDK 或 OTel + OTLP exporter

# 2. 送 sample events
# TODO: 觀察 trace 出現在 Honeycomb UI

# 3. 用 query 介面查詢
# TODO: SELECT count + visualize by service.name
```

## 日常操作與決策形狀

### Events vs metrics 心智模型

Honeycomb 跟 metrics-aggregation 平台不同。子議題：

- Event = 一個 trace span（包含 dozens of attributes）
- 不預先 aggregate、查詢時 group by 任意 attribute
- High-cardinality 不是問題、是設計目標
- 對應 [4.C7 Gaming peak cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)

### Instrumentation

子議題：

- **Honeycomb SDK**（Beeline）：簡單、Honeycomb-specific、auto-instrumentation 部分
- **OTel SDK + OTLP**：標準、vendor-neutral、推薦新部署用
- Manual attribute：對 business / domain context attribute 不省略
- Refinery：tail-based sampling proxy

### Query 介面

子議題：

- Visualize：count / count_distinct / heatmap / p50 / p95 / p99
- Group by：任意 attribute（user_id / region / version 等）
- Filter：WHERE clause
- 對應 SLO query：`heatmap(duration_ms) GROUP BY service.name WHERE http.status_code = 500`

## 進階主題（按需閱讀）

### BubbleUp 分析

子議題：

- 給定 heatmap 異常區、自動找區隔 outlier 跟 baseline 的 attribute
- 適合「我看到 latency spike、但不知道哪個維度造成」
- Unknown-unknowns 偵錯模式
- 跟 Datadog APM 的 service map 對照

### SLO 與 burn rate alert

子議題：

- SLO 配置（service + indicator + objective + window）
- Burn rate calculation：multi-window multi-burn-rate alert
- 跟 [knowledge cards burn-rate](/backend/knowledge-cards/burn-rate/) 對照
- 對應 [4.C9 OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/)

### Refinery（tail-based sampling）

子議題：

- 為什麼需要 tail-based：保留有錯 / 高延遲 trace、丟正常 trace
- Refinery 部署模式（gateway in front of Honeycomb）
- Sampling rule：error / latency / per-service / dynamic
- 對應成本：100% ingestion 太貴、tail-based 平衡

### OTLP integration

子議題：

- Honeycomb 接受 OTLP（gRPC / HTTP）
- 應用層用 OTel SDK、傳給 Honeycomb 不用改 SDK
- Multi-backend 支援：同一份 OTel data 送 Honeycomb + 其他
- 對應 [4.C2 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)

### 結構化 events 設計

子議題：

- 哪些 attribute 應加（user_id / request_id / business 維度）
- 哪些 attribute 不該加（PII / secrets）
- Wide events 哲學：一個 event 帶 dozens of attributes、不分散到多 metric
- 對應 PII redaction strategy

### Observability-driven development

子議題：

- Charity Majors 提的 SDLC 模式：production debug 是常態
- TDD + observability：寫 code 同時思考可觀測性
- 跟 SRE 文化整合

## 排錯快速判讀

### Events 沒到 Honeycomb

操作原則：先看 SDK 配置（API key + dataset）、再看 network、最後看 Honeycomb status page。

### Query timeout

操作原則：query window 過大或 attribute cardinality 過高造成 backend slow。判讀：縮 time window、簡化 group by。

### Sampling 過頭 vs 不足

操作原則：debug 時找不到 trace（sampling 過頭）vs cost 爆（sampling 不足）。Refinery 提供 dynamic sampling 解決靜態 rate 的不足。

### Burn rate alert noise

操作原則：multi-window 設計避免「短暫 spike 觸發 alert」、低 burn rate window 給長期趨勢。

### 跟其他 backend dual ship 不一致

對應 [4.C9 OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/)。判讀：兩個 backend 數據不對齊、看 SDK 是否 dual export、attribute mapping 是否一致。

## 何時改走其他服務

| 需求形狀                     | 改走                                                                                                                                   |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 廣度大、要 600+ integrations | [Datadog](/backend/04-observability/vendors/datadog/)                                                                                  |
| 預算敏感                     | [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（OSS）                                                               |
| Pure metrics                 | [Prometheus](/backend/04-observability/vendors/prometheus/)                                                                            |
| Logs full-text               | [Elastic Stack](/backend/04-observability/vendors/elastic-stack/)                                                                      |
| Error tracking 為主          | [Sentry](/backend/04-observability/vendors/sentry/)                                                                                    |
| Cloud-native (AWS / GCP)     | [CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) / [Cloud Ops](/backend/04-observability/vendors/gcp-cloud-operations/) |
| Self-hosted                  | OSS observability（Honeycomb 是 SaaS only）                                                                                            |

## 不在本頁內的主題

- Honeycomb SDK 完整 API
- BubbleUp 內部演算法
- Refinery 詳細配置
- Honeycomb pricing 詳細

## 案例回寫

### 直接相關案例

| 案例                                                                                                          | 主討論議題                     |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| [4.C7 Gaming peak cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/) | High-cardinality debug pattern |

### 跨 vendor 對照

| 案例                                                                                           | 對 Honeycomb 的對應                              |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [4.C9 OTel signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/) | Dual ship Honeycomb + 其他需驗證                 |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)     | Honeycomb 適合中大型 + observability-driven team |

**待補 Honeycomb 案例**：Charity Majors 的 production talks、Honeycomb customer engineering blog、Refinery scale-up case。

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)、[Datadog](/backend/04-observability/vendors/datadog/)
- 下游能力：[06 reliability 模組](/backend/06-reliability/)（SLO / burn rate）、[4.20 Evidence Package](/backend/04-observability/observability-evidence-package/)
