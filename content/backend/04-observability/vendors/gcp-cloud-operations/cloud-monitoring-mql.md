---
title: "Cloud Monitoring Metrics Model 與 MQL"
date: 2026-06-22
description: "說明 GCP Cloud Monitoring 的 monitored resource / metric descriptor 模型、MQL 與 PromQL 查詢、custom metrics 設計、alerting policy 與 Managed Prometheus 整合"
weight: 10
tags: ["backend", "observability", "gcp", "cloud-monitoring", "metrics"]
---

> 本文是 [GCP Cloud Operations](/backend/04-observability/vendors/gcp-cloud-operations/) 的 vendor deep article，深化 overview「Cloud Monitoring uptime checks / SLO」跟「OTLP integration」段。初次接觸 GCP 觀測的讀者建議先讀 [GCP Cloud Operations 服務頁](/backend/04-observability/vendors/gcp-cloud-operations/)。

## 問題情境

GCP 服務預設把 metrics 寫到 Cloud Monitoring，工程師打開 Metrics Explorer 就能看到 CPU、記憶體、request count。問題通常出在三個地方：GCP 內建 metrics 的 resource model 跟應用層的 business metrics 用不同語言描述同一件事，PromQL 使用者要重新學 MQL 語法，alerting policy 的 condition type 跟 notification channel 配置比預期複雜。理解 Cloud Monitoring 的 metrics model 才能避免 custom metrics 爆量、alert noise、跟 Prometheus 生態的銜接摩擦。

## 核心概念

### Monitored resource 與 metric descriptor

Cloud Monitoring 的資料模型有兩個軸：**monitored resource** 描述「誰產生了這個 metric」，**metric descriptor** 描述「這個 metric 量什麼」。

Monitored resource 是 GCP 自動帶入的標籤集合。GKE pod 的 monitored resource type 是 `k8s_pod`，帶 `project_id`、`location`、`cluster_name`、`namespace_name`、`pod_name`。Cloud Run revision 是 `cloud_run_revision`，帶 `service_name`、`revision_name`、`location`。這層標籤不需要工程師手動設定，GCP agent 或 SDK 自動填入。

Metric descriptor 定義 metric 的名稱、型別（GAUGE / DELTA / CUMULATIVE）、value type（INT64 / DOUBLE / DISTRIBUTION）與自訂 label。GCP 內建 metrics 用 `compute.googleapis.com/instance/cpu/utilization` 這樣的命名空間格式；custom metrics 用 `custom.googleapis.com/<your-name>` 或 `workload.googleapis.com/<your-name>`（後者透過 OTel Collector 或 Managed Prometheus 寫入時使用）。

兩個軸相乘就是 time series 的數量。Cardinality 管理在 GCP 上等同於控制 monitored resource × metric label 的組合數。GCP 對 custom metrics 有每個 project 的 time series 配額（預設 500 per metric descriptor、可申請提高），超過時寫入會被拒。

### MQL vs PromQL

Cloud Monitoring 有兩種查詢語言。MQL（Monitoring Query Language）是 GCP 自家設計的 pipeline 語法：

```text
fetch k8s_container
| metric 'kubernetes.io/container/cpu/core_usage_time'
| align rate(1m)
| every 1m
| group_by [resource.cluster_name, resource.namespace_name],
    [value_cpu_usage: aggregate(value.core_usage_time)]
```

PromQL 在 Cloud Monitoring 上也可用（透過 Managed Service for Prometheus）。兩者的核心差異：

| 面向             | MQL                                   | PromQL（via Managed Prometheus）       |
| ---------------- | ------------------------------------- | -------------------------------------- |
| 資料來源         | 所有 Cloud Monitoring metrics         | 透過 Managed Prometheus 寫入的 metrics |
| 查詢介面         | Metrics Explorer / alerting condition | Grafana / Prometheus UI / API          |
| Aggregation 語法 | pipe-style `group_by`                 | 函式風格 `sum by (label)`              |
| 跨 GCP 與 custom | 原生支援 GCP 內建 metrics             | 需要轉成 Prometheus 格式               |
| 學習曲線         | GCP-specific、不可搬到其他平台        | 跨平台標準、可搬到 Mimir / Thanos      |

選擇判讀：純 GCP 環境且團隊沒有 Prometheus 經驗 → MQL 起步快。已有 Prometheus / Grafana 生態 → 用 Managed Prometheus + PromQL、把 GCP 內建 metrics 透過 Prometheus-compatible exporter 導入。混合環境 → 兩者並存、GCP 原生 metrics 用 MQL 做 alerting、application metrics 用 PromQL 查詢。

## 配置 step-by-step

### Custom metrics 設計與寫入

Custom metrics 的常見路徑有三條：

**路徑一：Cloud Monitoring API 直接寫入**。應用程式用 Cloud Monitoring client library 建立 metric descriptor 並寫入 time series。適合 GCP-native 應用，不需要額外 agent。

```text
metric type: custom.googleapis.com/checkout/latency_ms
kind: GAUGE
value type: DISTRIBUTION
labels: [service, region, status_code]
```

**路徑二：OTel Collector + GCP exporter**。應用程式用 OTel SDK 產生 metrics，OTel Collector 透過 `googlecloud` exporter 寫到 Cloud Monitoring。Metrics 命名空間是 `workload.googleapis.com/`。適合已有 OTel instrumentation 的服務。

**路徑三：Managed Service for Prometheus**。部署 GCP 的 Managed Prometheus collector（或自管 Prometheus + remote write），metrics 存在 GCP 託管的 Monarch backend。查詢用 PromQL。適合 Kubernetes 環境且團隊熟悉 Prometheus 生態。

三條路徑可以共存。選擇判讀：先看團隊的 metrics 生態是 GCP-native 還是 Prometheus-native，再看 multi-cloud 需求。Managed Prometheus 的優勢是 PromQL 可搬、劣勢是 GCP 內建 metrics 需要額外整合。

### Alerting policy 配置

Cloud Monitoring alerting policy 由三部分組成：condition、notification channel、documentation。

Condition types：

- **Metric threshold**：metric 超過閾值 N 分鐘。適合「error rate > 1% 持續 5 分鐘」。
- **Metric absence**：metric 消失。適合偵測 scrape 斷裂或服務停擺。
- **Forecasting**：預測 metric 在 N 小時後超過閾值。適合 disk 滿、quota 耗盡。
- **Process health**：GCE instance 的 process 是否存活。
- **Log-based**：Cloud Logging 出現特定 pattern 時觸發。適合把 error log 轉成 alert。
- **SLO burn rate**：SLO 設定後、burn rate 超過閾值。對應 [burn-rate](/backend/knowledge-cards/burn-rate/) 概念。

Notification channels：Email / PagerDuty / Slack / Pub/Sub / Webhook / SMS。Pub/Sub channel 適合接自定義 automation（收到 alert → trigger Cloud Function）。

Snooze 與 maintenance window：暫時抑制特定 alerting policy。部署期間或已知維護時使用。

### Managed Prometheus 整合

GCP Managed Service for Prometheus 的部署模式：

- **GKE 模式**：啟用 GKE monitoring、Managed Prometheus collector 自動部署。不需要自管 Prometheus server。
- **Remote write 模式**：自管 Prometheus server + `remote_write` 到 GCP Monarch endpoint。保留本地查詢能力，同時長期儲存在 GCP。
- **OTel Collector 模式**：OTel Collector 用 `googlemanagedprometheus` exporter 寫到 Monarch。

查詢端：用 GCP Console 的 PromQL UI、或部署 Grafana + GMP datasource。PromQL 功能子集支援良好（rate / histogram_quantile / aggregation），少數進階功能（subquery）有限制。

## 故障演練與邊界

### Custom metric 配額用盡

**觸發條件**：custom metric descriptor 數量超過 project 配額（預設 500），或單一 metric descriptor 的 time series 數量超過配額。

**表現**：API 回傳 429 或 quota exceeded error。新 time series 寫不進去，既有的不受影響。

**修復**：清理不再使用的 metric descriptor（describe → delete）、合併語意重疊的 metrics、減少 label cardinality。GCP Console → IAM → Quotas 可以申請提高配額，但先確認是設計問題而非真的需要那麼多 series。

### Alerting policy 觸發延遲

**觸發條件**：alerting policy 使用的 metrics 的 alignment period 或 duration 設定過長。

**表現**：異常已經發生 10 分鐘，alert 才觸發。原因是 Cloud Monitoring 的 evaluation cycle 跟 metrics ingestion delay 相加。GCP 內建 metrics 的 ingestion delay 約 1-3 分鐘；custom metrics 透過 API 寫入的 delay 約 10-30 秒。

**修復**：把 condition 的 alignment period 設短（1 分鐘）、duration 設短（但太短會造成 flapping）。Log-based alerting condition 的 delay 通常比 metric-based 短（秒級 vs 分鐘級），緊急異常考慮用 log-based condition。

### Managed Prometheus 查詢與自管 Prometheus 結果不一致

**觸發條件**：同一個 PromQL query 在本地 Prometheus 跟 GMP 的結果不同。

**表現**：dashboard 數字對不上、alert 觸發行為不一致。

**修復**：先確認 remote write 是否有 sample drop（看 `prometheus_remote_storage_samples_failed_total`）。再確認 GMP 的 PromQL 子集限制（部分 subquery 語法不支援）。最後確認 metric naming：local Prometheus 的 metric name 跟 GMP 儲存後的 naming convention 可能有差異（加了 `__name__` prefix 或 resource label）。

## 容量與成本

Cloud Monitoring 的計費模型基於 **ingested metrics volume**（per million data points）。GCP 內建 metrics（agent metrics 除外）免費。Custom metrics 的前 150 MB per billing account 免費，超過後按 volume 計費。

成本治理的判讀：

- 最大成本來源通常是高頻率的 custom metrics 或高 cardinality label
- 用 `monitoring.googleapis.com/billing/bytes_ingested` metric 追蹤 ingestion 量
- 減少 scrape interval（15s → 30s 或 60s）可以直接降低 ingestion 量
- Managed Prometheus 的計費跟 custom metrics 分開計算（per samples ingested）

## 整合與下一步

- [GCP Cloud Operations 服務頁](/backend/04-observability/vendors/gcp-cloud-operations/)：overview 與日常操作
- [4.7 cardinality 治理](/backend/04-observability/cardinality-cost-governance/)：cardinality 治理的完整策略
- [4.6 SLI/SLO signal](/backend/04-observability/sli-slo-signal/)：SLO burn rate alert 的訊號設計
- [Prometheus](/backend/04-observability/vendors/prometheus/)：Managed Prometheus 的上游概念
- [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)：OTel Collector + GCP exporter 整合
- [Cloud Logging 查詢、匯出與合規](../cloud-logging-export-compliance/)：同 vendor 的 logs 面
