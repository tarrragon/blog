---
title: "AWS CloudWatch"
date: 2026-05-01
description: "AWS 原生觀測性服務、Logs / Metrics / Traces (X-Ray)"
weight: 7
tags: ["backend", "observability", "vendor"]
---

CloudWatch 是 AWS 原生 observability 服務、承擔三個責任：AWS 服務內建 metrics / logs / alarms（無需配置）、跨 AWS 服務統一觀測平面、X-Ray + Container Insights + Lambda Insights 等專用擴展。設計取捨偏向「AWS 生態深度整合 + 不用第三方 vendor + 預設 turnkey」、跨雲跟成本是主要限制。

## 本章目標

讀完本章後、你應該能：

1. 用 AWS CLI / Console 查 CloudWatch metrics / logs / alarms
2. 用 CloudWatch Logs Insights 查詢結構化 logs
3. 配置 alarm + composite alarm + EventBridge integration
4. 用 X-Ray 追蹤 distributed tracing
5. 控制 CloudWatch cost（log ingestion / metric / API call）

## 最短路徑：5 分鐘把 CloudWatch 跑起來

```bash
# 1. 用 CloudWatch Agent 採集 EC2 metrics + logs
# TODO: aws-cli + cloudwatch-agent.json config

# 2. 查詢 metric
# TODO: aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization

# 3. 用 Logs Insights 查詢
# TODO: fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc
```

## 日常操作與決策形狀

### Metrics / Logs / Alarms 整合

子議題：

- Namespace + Dimension + Metric 三層
- Custom metric（CLI / SDK / Agent）
- Logs group + Log stream + Log event
- Alarm + Composite alarm + EventBridge rule

### Logs Insights query

子議題：

- Query syntax：fields / filter / parse / stats / sort
- 跟 KQL / LogQL 對照（CloudWatch 自家 syntax）
- 對應指令：`aws logs start-query`、`aws logs get-query-results`

### Metrics Math

子議題：

- 跨 metric 算術運算（rate / sum / avg）
- 適合 dashboard / alarm 不直接 metric 表達的計算
- 對比 PromQL：CloudWatch Math 較弱、無 label join 能力

### X-Ray tracing

子議題：

- 各語言 X-Ray SDK
- Sampling rule（rate-based / reservoir）
- Service map 自動 build
- 對應 [4.C4 X-Ray to OpenTelemetry](/backend/04-observability/cases/xray-to-opentelemetry-migration/) 遷移案例

## Deep Article

- [Logs Insights 查詢與日誌治理](logs-insights-governance/)：log group 設計、query syntax、retention policy、cross-account aggregation、subscription filter 與 cost governance
- [Alarms 與 Composite Alarms 操作實務](alarms-composite-operations/)：Metric Alarm、Anomaly Detection、Composite Alarm 設計、alarm actions、missing data 處理與 cost

## 進階主題（按需閱讀）

### Container Insights / Lambda Insights

子議題：

- Container Insights：EKS / ECS metrics + logs 自動採集
- Lambda Insights：Lambda runtime metrics + cold start visibility
- 跟 Prometheus + Grafana 的 K8s 模式對照

### CloudWatch Synthetics / RUM

子議題：

- Synthetics：canary script 定期 probe
- RUM：前端用戶體驗
- 跟 Datadog Synthetics / RUM 對照

### Logs lifecycle

子議題：

- Retention（1 day to never expire）
- Subscription filter：把 logs 送到 Lambda / Kinesis / S3
- Logs to S3 archive
- 對應 cost 控制

### Cost 控制

子議題：

- Logs ingestion charge（per GB）
- Metrics storage charge（custom metrics + high-resolution）
- API call charge（GetMetricData / Logs Insights query）
- 對應 [4.C1 Fintech audit](/backend/04-observability/cases/fintech-audit-evidence-observability/)

### CloudWatch Managed Prometheus（AMP）

子議題：

- AMP：AWS managed Prometheus、scrape EKS / ECS
- 跟 CloudWatch 互補（CloudWatch 是 AWS-native、AMP 是 OSS standard）
- 對應 [4.C6 ADOT EKS](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/)

### AWS Distro for OpenTelemetry（ADOT）

子議題：

- AWS-supported OTel distribution
- 跟 X-Ray / AMP / CloudWatch 都整合
- 推薦的 OTel adoption 路徑
- 對應 [4.C6 ADOT EKS](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/)

## 排錯快速判讀

### Logs Insights query 過慢

操作原則：query 範圍 + 結果集大時、用 sample 縮範圍。

```bash
# TODO: fields @timestamp, @message | limit 100（先測 logic）
```

### Metric not found

操作原則：metric namespace / dimension 對應錯。判讀：用 `aws cloudwatch list-metrics --namespace ...` 確認。

### Alarm 沒觸發

操作原則：alarm period / evaluation period / datapoints 配置造成延遲或忽略。

### X-Ray trace incomplete

操作原則：sampling rule 過頭、subseg context propagation 失敗。判讀：X-Ray console 看 trace timeline。

### Cost 爆

操作原則：log ingestion 多、custom metric 多、Logs Insights query 量大都會貢獻。判讀：Cost Explorer 看 CloudWatch service breakdown。

## 何時改走其他服務

| 需求形狀              | 改走                                                                                                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 多雲 / 跨雲統一       | [Datadog](/backend/04-observability/vendors/datadog/) / [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) / [OTel](/backend/04-observability/vendors/opentelemetry/) |
| 進階 APM 體驗         | [Datadog](/backend/04-observability/vendors/datadog/) / [Honeycomb](/backend/04-observability/vendors/honeycomb/)                                                                    |
| 高頻 query / 大量 log | [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（Loki）/ [Elastic](/backend/04-observability/vendors/elastic-stack/)                                               |
| OTel standard         | [OTel](/backend/04-observability/vendors/opentelemetry/) + ADOT / AMP                                                                                                                |
| GCP / Azure 生態      | [Cloud Operations](/backend/04-observability/vendors/gcp-cloud-operations/) / Azure Monitor                                                                                          |

## 不在本頁內的主題

- 各 AWS 服務的 CloudWatch metric 名稱列表
- CloudWatch Synthetics canary script 語法
- Logs Insights 完整 query syntax reference
- AWS IAM 跟 CloudWatch 的細部權限

## 案例回寫

### 直接相關案例

| 案例                                                                                                 | 主討論議題            |
| ---------------------------------------------------------------------------------------------------- | --------------------- |
| [4.C4 X-Ray to OTel](/backend/04-observability/cases/xray-to-opentelemetry-migration/)               | X-Ray 遷出到 OTel     |
| [4.C6 ADOT EKS pipeline](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/) | AWS Distro + EKS 觀測 |

### 跨 vendor 對照

| 案例                                                                                                       | 對 CloudWatch 的對應                             |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [4.C1 Fintech audit](/backend/04-observability/cases/fintech-audit-evidence-observability/)                | CloudWatch Logs / S3 archive 作為 audit evidence |
| [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/) | Logs lifecycle / retention 對應資料主權限制      |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)                 | AWS-only 場景優先 CloudWatch                     |

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)、[Cloud Operations](/backend/04-observability/vendors/gcp-cloud-operations/)
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
