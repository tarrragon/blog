---
title: "Prometheus"
date: 2026-05-01
description: "Pull-based metrics 主流 OSS、PromQL 與 alerting"
weight: 2
tags: ["backend", "observability", "vendor"]
---

Prometheus 是 CNCF graduated 的 metrics 系統、承擔三個責任：pull-based metrics scraping（service discovery + scrape）、PromQL 查詢與 recording rules、Alertmanager 告警與路由。設計取捨偏向「短中期 metrics + 簡單部署 + cloud-native 整合」、長期儲存交給 Mimir / Thanos / Cortex。是 Kubernetes 生態 metrics 的事實標準。

對「K8s metrics、service metrics、需要 PromQL 表達能力、自管 metrics 棧」這條路徑、Prometheus 是首選。

## 本章目標

讀完本章後、你應該能：

1. 用 docker 跑起 Prometheus、配置 scrape target
2. 用 PromQL 查詢 metrics、寫 recording rules / alerting rules
3. 設計 service discovery（K8s / Consul / file_sd）
4. 看懂 cardinality 訊號、避免 label explosion
5. 評估長期儲存（Thanos / Mimir / Cortex）跟 remote write 的選擇

## 最短路徑：5 分鐘把 Prometheus 跑起來

```bash
# 1. 啟動 Prometheus（含 sample config）
# TODO: docker run -p 9090:9090 -v ./prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

# 2. 配置 scrape target（prometheus.yml）
# TODO: scrape_configs with static_configs / kubernetes_sd_configs

# 3. 查詢驗證
# TODO: 瀏覽器訪 http://localhost:9090、用 PromQL 查 `up`
```

最短路徑驗證 Prometheus 起來、能 scrape 跟查詢。實際 production 要配 retention + alerting + HA。

## 日常操作與決策形狀

### Scrape 配置與 service discovery

子議題：

- Static config：手動列 target、適合小規模
- File SD：動態檔案、適合外部系統推送
- Kubernetes SD：K8s API server 動態發現
- Consul SD：跟 Consul service registry 整合
- 對應配置：`scrape_configs` 區段

### PromQL 查詢

子議題：

- Instant query vs range query
- Aggregation：sum / avg / max / min / count + by / without
- Rate / increase（counter 處理）
- Histogram quantile（histogram_quantile + bucket）
- 對應指令：HTTP API `/api/v1/query`

### Recording rules / Alerting rules

子議題：

- Recording rules：預先計算昂貴 query、降低 dashboard 查詢成本
- Alerting rules：定義 alert condition + for duration + labels / annotations
- Alertmanager：去重 / 抑制 / 分組 / routing
- 對應配置：`rule_files`

## Deep Article

- [Prometheus 容量規劃與故障模式](capacity-failure-modes/)：單機容量邊界、cardinality 與 retention 的資源模型、常見故障模式與判讀

## 進階主題（按需閱讀）

### High availability

子議題：

- Prometheus 沒原生 HA — 跑兩個 instance scrape 同 target、靠下游去重
- Thanos：sidecar 模式、跨 Prometheus instance 查詢統一
- Mimir：fully replicated metric storage（多 Prometheus → Mimir）
- 對應案例 [4.C8 Airbnb K8s scale signals](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)

### Cardinality 管理

對應案例 [4.C2 Gaming peak cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)。子議題：

- Cardinality = unique label combinations 數量
- High-cardinality label（user_id / request_id / trace_id）會炸 Prometheus
- 偵測：`prometheus_tsdb_head_series` metric
- 修法：drop label / aggregation / 改用 traces backend（Honeycomb）

### Remote write / read

子議題：

- Remote write：Prometheus → 長期儲存（Mimir / Cortex / Thanos / Datadog / Grafana Cloud）
- Remote read：查詢時拉長期儲存資料
- 用 receiver / agent 模式（無 local TSDB）
- 對應配置：`remote_write` / `remote_read`

### Exporters 生態

子議題：

- Node exporter（host metrics）
- Blackbox exporter（HTTP / TCP / ICMP probing）
- Database exporters（postgres / mysql / redis）
- 應用層 metrics：用 client library（prometheus_client）原生暴露
- 對應 ServiceMonitor / PodMonitor（Prometheus Operator）

### Prometheus Operator（K8s）

子議題：

- CRD：Prometheus / ServiceMonitor / PodMonitor / PrometheusRule / Alertmanager
- 自動發現 ServiceMonitor 物件、不手動改 scrape config
- kube-prometheus-stack Helm chart
- 對應 [4.C6 ADOT EKS](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/) 對照

### Pull vs Push model

子議題：

- Pull model（Prometheus default）：service discovery、health check 自然
- Push model（Pushgateway）：適合 short-lived job、不建議常駐 service
- 為何 Pushgateway 不推：cardinality 不易管、scrape semantics 違反

## 排錯快速判讀

### Scrape failure

操作原則：先看 target 是否健康、再看 network 跟認證。

```bash
# TODO: HTTP /targets endpoint 看 scrape status
```

### Cardinality explosion

操作原則：series 數量持續增長、可能 OOM。

```bash
# TODO: 查 `prometheus_tsdb_head_series` 跟 `prometheus_tsdb_head_active_appenders`
```

對應 [4.C2 Gaming peak](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/) 的處理路徑。

### Query 過慢

操作原則：query 過大範圍 / aggregation 過多 → Recording rules 預先聚合。

### Alert flapping / noise

操作原則：alert 觸發頻繁但無實際問題、調整 `for:` duration、加 absent() check、用 Alertmanager inhibition。

### Memory pressure

操作原則：Prometheus retention 跟 cardinality 決定 memory。判讀：cardinality 太大 → remote write 卸載長期儲存。

## 何時改走其他服務

| 需求形狀               | 改走                                                                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 長期 retention（年級） | Thanos / Mimir / Cortex / [Grafana Cloud](/backend/04-observability/vendors/grafana-stack/)                                                  |
| 需要 logs / traces     | [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) (Loki/Tempo) / [Elastic](/backend/04-observability/vendors/elastic-stack/) |
| Auto-instrumentation   | [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/) + Prometheus exporter                                                      |
| SaaS turnkey           | [Datadog](/backend/04-observability/vendors/datadog/)                                                                                        |
| High-cardinality debug | [Honeycomb](/backend/04-observability/vendors/honeycomb/)                                                                                    |
| AWS-native             | [CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) + Managed Prometheus                                                         |
| Pure push model        | StatsD / InfluxDB（不在本模組）                                                                                                              |

## 不在本頁內的主題

- PromQL 完整 syntax reference（prometheus.io/docs/prometheus/latest/querying/）
- Exporter 內部實作
- Alertmanager routing tree 細節
- Operator CRD spec

## 案例回寫

### 直接相關案例

| 案例                                                                                                          | 主討論議題                        |
| ------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| [4.C2 Gaming peak cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/) | Cardinality 管理 / freshness 取捨 |
| [4.C6 ADOT EKS](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/)                   | AWS Distro + Prometheus 整合      |
| [4.C8 Airbnb K8s scale](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)              | K8s metrics + Prometheus 規模化   |

### 跨 vendor 對照

| 案例                                                                                                     | 對 Prometheus 的對應                           |
| -------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)          | 從 Prometheus + Datadog 雙軌走向 OTel 對齊     |
| [4.C9 OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/) | （反例）Prometheus 指標跟新管線的語意對不齊    |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)               | 小型單 instance / 中型 Operator / 大型 + Mimir |

## 下一步路由

- 上游概念：[Metrics Basics](/backend/04-observability/metrics-basics/)
- 平行 vendor：[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（Mimir）、[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
