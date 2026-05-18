---
title: "Elastic Stack"
date: 2026-05-01
description: "ELK：Elasticsearch / Logstash / Kibana + Beats / APM"
weight: 5
tags: ["backend", "observability", "vendor"]
---

Elastic Stack（前 ELK）是 logs-heavy observability 棧、承擔三個責任：Elasticsearch 搜尋與分析（full-text + structured query）、Beats / Logstash 採集 pipeline、Kibana 視覺化 + Elastic APM（traces）。設計取捨偏向「搜尋為核心 + 統一搜尋介面 + Elastic Security SIEM 整合」。AWS 因 2021 license 變動 fork OpenSearch、提供 Apache 2.0 替代。

## 本章目標

讀完本章後、你應該能：

1. 部署 Elasticsearch + Kibana + Beats 基本棧
2. 用 KQL / Lucene 查詢 logs、用 ES DSL 寫進階搜尋
3. 設計 index lifecycle（hot / warm / cold / frozen）
4. 評估 Beats / Logstash / Fluent Bit / Vector 的採集選擇
5. 評估 Elastic License vs OpenSearch fork 的取捨

## 最短路徑：5 分鐘把 Elastic Stack 跑起來

```bash
# 1. 用 docker-compose 跑 ES + Kibana
# TODO: docker-compose.yml with elasticsearch + kibana

# 2. 用 Filebeat 採集 host logs
# TODO: filebeat.yml with inputs + output.elasticsearch

# 3. 在 Kibana 查詢驗證
# TODO: KQL: `@timestamp >= now-15m AND log.level: "error"`
```

## 日常操作與決策形狀

### 採集 pipeline

子議題：

- Beats（Filebeat / Metricbeat / Packetbeat / Heartbeat / Auditbeat）：輕量、各自專屬
- Logstash：重型 ETL（grok parsing / enrichment / 多 output）
- Fluent Bit / Vector：替代採集 agent（更輕量、OSS）
- 對應 [4.C6 ADOT EKS](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/) 對照

### 查詢語法

子議題：

- KQL（Kibana Query Language）：直覺、適合日常查詢
- Lucene query string：複雜搜尋、boolean operators
- ES DSL（JSON）：API 級進階查詢
- ES|QL（Elastic Query Language、ES 8.11+）：類 SQL pipeline 語法

### Index 設計

子議題：

- Index template（mapping / settings）
- Data streams（time-series log / metrics）
- Field types：keyword / text / date / numeric / object / nested
- Dynamic mapping 風險：unbounded field 爆 index

### Index Lifecycle Management（ILM）

子議題：

- Hot phase：active write
- Warm phase：read-only、查詢頻率低
- Cold phase：searchable snapshot（S3 / object storage）
- Frozen phase（ES 7.12+）：searchable snapshot + minimal cluster resource
- Delete phase

## 進階主題（按需閱讀）

### Elastic APM

子議題：

- APM Server 接收 trace data
- 各語言 APM agent（Java / Python / Node / .NET / Go / Ruby / PHP）
- 接受 OTLP（ES 7.16+）
- Service map / dependency 視覺化

### Elastic Security（SIEM）

子議題：

- SIEM dashboard / detection rule
- ECS（Elastic Common Schema）跨資料統一 field naming
- Sigma rule import
- 跟 [07 security 模組](/backend/07-security-data-protection/) 對照

### Cluster scaling

子議題：

- Node roles：master / data / ingest / coordinating / ML / transform
- Hot-warm-cold architecture
- Shard sizing（推薦 20-40GB per shard）
- Cross-cluster search / replication

### Elastic License vs OpenSearch fork

子議題：

- 2021 Elastic 改 ELv2 / SSPL（非 OSI 認可）— AWS 不能提供「Elasticsearch as a Service」
- AWS fork OpenSearch（Apache 2.0、基於 ES 7.10）
- OpenSearch 持續演進、跟 ES 功能逐漸分歧
- 選擇判讀：合規 → OpenSearch；要最新 ES feature → Elastic

### Searchable Snapshots

子議題：

- 把 cold/frozen index 存 S3 / GCS / Azure Blob
- 查詢時動態 hydrate、成本降 80%+
- 適合 logs retention 長但查詢頻率低
- 對應 [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)

### Vector / Fluent Bit 採集替代

子議題：

- 為何用 Vector / Fluent Bit：更輕、resource 用量低
- Beats 在 K8s 跑起來資源耗較大
- 對應 cost 跟 maintainability 取捨

## 排錯快速判讀

### Index mapping explosion

操作原則：dynamic mapping 對未知 field 自動建 index、大量 field 爆 ES。

```bash
# TODO: GET /_cat/indices?v 看 field count
# TODO: PUT index/_mapping 鎖定 fields
```

### Cluster yellow / red

操作原則：cluster status 影響 query。

```bash
# TODO: GET /_cluster/health
# TODO: GET /_cat/shards?v 看 unassigned shards
```

### Query 過慢

操作原則：query 結果 > 10K → 用 search_after / scroll；text field 上做 aggregation → 改 keyword field。

### Disk pressure

操作原則：cluster disk > 85% → ES 進 read-only 模式。判讀：cluster.routing.allocation.disk.watermark。

### Logstash backpressure

操作原則：Logstash queue full → upstream Beats 累積 backpressure。判讀：Logstash monitoring page。

## 何時改走其他服務

| 需求形狀               | 改走                                                                                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Pure metrics           | [Prometheus](/backend/04-observability/vendors/prometheus/) / Mimir                                                                             |
| 純 logs 但 less search | Loki（[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)）— 更便宜                                                               |
| SaaS turnkey APM       | [Datadog](/backend/04-observability/vendors/datadog/)                                                                                           |
| AWS-managed Elastic    | OpenSearch on AWS（Apache 2.0）                                                                                                                 |
| Cloud-native logs      | [CloudWatch Logs](/backend/04-observability/vendors/aws-cloudwatch/) / [Cloud Logging](/backend/04-observability/vendors/gcp-cloud-operations/) |
| 多 tier observability  | [Datadog](/backend/04-observability/vendors/datadog/) / [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)                       |
| Enterprise SIEM        | Splunk / Microsoft Sentinel                                                                                                                     |

## 不在本頁內的主題

- ES query DSL 完整 reference
- Lucene scoring 演算法
- Kibana dashboard 美術
- Elastic ML / Anomaly Detection 細節

## 案例回寫

### 直接相關案例

| 案例                                                                                                       | 主討論議題                  |
| ---------------------------------------------------------------------------------------------------------- | --------------------------- |
| [4.C1 Fintech audit](/backend/04-observability/cases/fintech-audit-evidence-observability/)                | Logs 作為 audit evidence    |
| [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/) | Index Lifecycle / retention |

### 跨 vendor 對照

| 案例                                                                                                 | 對 Elastic Stack 的對應                                      |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [4.C6 ADOT EKS pipeline](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/) | Beats / Logstash ↔ OTel Collector 採集 pipeline 對照         |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)           | 小型 single-node / 中型 hot-warm / 大型 hot-warm-cold-frozen |

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（Loki 對照）、[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)
- 下游能力：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
