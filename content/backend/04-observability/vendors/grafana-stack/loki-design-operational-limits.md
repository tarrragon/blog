---
title: "Grafana Loki 設計與操作限制"
date: 2026-06-23
description: "說明 Loki 的 label-based 設計哲學、跟 Elasticsearch 的根本差異、label cardinality 限制、LogQL 查詢模式與成本模型"
weight: 11
tags: ["backend", "observability", "grafana", "loki", "logs"]
---

> 本文是 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) 的 vendor deep article，深化 overview「Loki 設計與限制」段。初次接觸 Grafana Stack 的讀者建議先讀 [Grafana Stack 服務頁](/backend/04-observability/vendors/grafana-stack/)。

## 問題情境

團隊從 ELK stack 或 CloudWatch Logs 遷到 Grafana Stack 時，Loki 是 log backend 的預設選擇。遷移後最常遇到的衝擊是查詢模式的根本差異：Elasticsearch 做 full-text index（寫入時索引每個欄位、查詢時任意搜尋），Loki 只 index labels（寫入時只索引 stream labels、查詢時先篩 stream 再 grep content）。

這個差異是刻意的設計選擇 — Loki 的目標是「Prometheus for logs」：用跟 Prometheus metrics 相同的 label 體系管理 logs，讓 log 查詢跟 metric 查詢使用同一組 label selector。代價是失去 full-text search 的即時性。理解這個設計哲學才能正確設計 label、寫出有效率的 LogQL、避免常見的效能陷阱。

## 核心概念

### Like Prometheus, but for logs

Prometheus 用 label set 識別 time series — `{job="checkout", instance="10.0.1.5"}` 是一條 series。Loki 用相同概念識別 log stream — `{job="checkout", namespace="production"}` 是一條 stream。同一條 stream 的所有 log entries 存在同一組 chunks。

Elasticsearch 的索引模式是「寫入時建 inverted index、查詢時走索引」。Loki 的索引模式是「寫入時只記錄 stream label → chunk 的 mapping、查詢時先用 label 選 stream、再在 chunk 內做 grep」。

這代表：

- **有 label filter 的查詢很快** — Loki 只掃對應 stream 的 chunks
- **沒有 label filter 的查詢很慢** — Loki 要掃所有 stream 的 chunks（相當於 full scan）
- **Label cardinality 跟 Prometheus 一樣敏感** — 高 cardinality label 產生大量 stream、每個 stream 的 chunk 很小、index 膨脹

### Stream 與 chunk

一條 stream = 一組唯一的 label set。每條 stream 的 log entries 依時間排序存在 chunks 裡。Chunk 是 Loki 的最小儲存單位。

```text
Stream: {job="checkout", namespace="production"}
  └─ Chunk 1: [2026-06-22T00:00 ~ 2026-06-22T01:00] (compressed)
  └─ Chunk 2: [2026-06-22T01:00 ~ 2026-06-22T02:00] (compressed)
  └─ ...
```

Chunk 存在 object storage（S3 / GCS / MinIO），index 存在 key-value store（BoltDB / TSDB，3.0 起預設 TSDB）。Object storage 便宜（相比 Elasticsearch 的 SSD），這是 Loki 成本優勢的來源。

### 跟 Elasticsearch 的根本差異

| 面向             | Loki                                           | Elasticsearch                                 |
| ---------------- | ---------------------------------------------- | --------------------------------------------- |
| 索引對象         | 只索引 labels（stream metadata）               | 索引所有欄位（full-text + structured）        |
| 查詢模式         | Label selector → stream → grep content         | Query DSL / KQL → inverted index lookup       |
| 寫入成本         | 低（不建 content index）                       | 高（建 inverted index + doc values）          |
| 查詢成本         | 取決於 stream 篩選效率（label 越精準越快）     | 取決於 index 覆蓋度（indexed field 查詢快）   |
| 儲存成本         | 低（object storage）                           | 高（SSD / local disk）                        |
| Full-text search | 不支援（只有 line filter grep）                | 原生支援                                      |
| 適用場景         | 已有 Prometheus/Grafana 生態的 log aggregation | 需要 full-text search 的 log analytics / SIEM |

判讀：如果團隊的 log 查詢模式是「先選 service/namespace/pod、再看時間範圍內的 log entries」，Loki 足夠。如果查詢模式是「在所有 log 裡搜某個 error message 或 request ID」，Elasticsearch 的 full-text index 更適合。

## 配置 step-by-step

### Label 設計原則

Label 設計是 Loki 最重要的操作決策。原則跟 Prometheus 相同：低 cardinality、穩定、有查詢意義。

| Label                      | Cardinality         | 適合當 label | 理由                                             |
| -------------------------- | ------------------- | ------------ | ------------------------------------------------ |
| `job`                      | 低（服務數量）      | 適合         | 篩選到特定服務                                   |
| `namespace`                | 低                  | 適合         | 篩選到特定環境                                   |
| `pod_name`                 | 中（pod 數量）      | 視情境       | K8s 環境常用但 pod 頻繁重建會產生大量短命 stream |
| `level`（info/warn/error） | 低（3-5 值）        | 適合         | 快速篩選 error log                               |
| `request_id`               | 極高（per-request） | 不適合       | 每個 request 一條 stream、chunk 極小、index 爆炸 |
| `user_id`                  | 高                  | 不適合       | 同上                                             |
| `trace_id`                 | 極高                | 不適合       | 用 Tempo 查 trace、不用 Loki label               |

request_id / user_id / trace_id 不應該是 label，它們應該在 log content 裡用 structured JSON 欄位表達，查詢時用 LogQL 的 line filter 或 parser 提取。

### LogQL 常見查詢模式

**Stream selector + line filter**（最基本）：

```logql
{job="checkout", namespace="production"} |= "error" |= "timeout"
```

先選 stream、再 grep 包含 "error" 和 "timeout" 的 log lines。`|=` 是包含、`!=` 是不包含、`|~` 是 regex。

**Structured metadata parser**（JSON log）：

```logql
{job="checkout"} | json | status_code >= 500 | line_format "{{.method}} {{.path}} {{.status_code}}"
```

`| json` 解析 JSON log entry 的欄位，後續可以用欄位做 filter 和格式化。

**Metric 聚合**（log → metric）：

```logql
sum by (status_code) (rate({job="checkout"} | json | __error__="" [5m]))
```

計算每 5 分鐘每個 status_code 的 log entry 速率。這是 Loki 的「metric from logs」能力 — 不需要額外的 metrics pipeline，直接從 log 產生 time series。

### Loki config 核心段

```yaml
# loki-config.yaml
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: loki_index_
        period: 24h

storage_config:
  tsdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
  aws:
    s3: s3://loki-chunks-bucket
    region: us-east-1

limits_config:
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  max_streams_per_user: 10000
  max_label_name_length: 1024
  max_label_value_length: 2048
```

`limits_config` 是防護網。`max_streams_per_user` 限制每個 tenant 的 stream 數量，超過時新 stream 的 log 被拒（HTTP 429）。這是 label cardinality 爆炸的最後防線。

## 故障與邊界

### Label cardinality 爆炸

**觸發條件**：label 包含高 cardinality 值（pod UID、request ID、container ID）。每個唯一 label set 產生一條 stream，stream 數量快速增長。

**表現**：`loki_ingester_memory_streams` 持續上升、ingester memory 增長、最終觸發 `max_streams_per_user` 限制（429 error）。跟 Prometheus series explosion 是同一個問題的 log 版本。

**修法**：檢查產出大量 stream 的 label。Loki 的 `/loki/api/v1/labels` 和 `/loki/api/v1/label/{name}/values` API 可以列出所有 label 值。找到高 cardinality label 後，從 promtail / alloy 的 pipeline 中移除該 label、改放進 log content 的 structured field。

### Stream rate limit

**觸發條件**：單一 stream 的 ingestion rate 超過 `per_stream_rate_limit`（預設 3 MB/s）。通常是某個 service 大量噴 debug log。

**表現**：Loki 回傳 429 + `rate limit exceeded` error。部分 log entries 被丟棄。

**修法**：先解決 log 噴量問題（降低 debug log level 或加 sampling）。如果噴量合理（高 QPS 服務），調高 `per_stream_rate_limit` 或拆分 stream（加一層 label 分散流量）。

### 大時間範圍查詢 timeout

**觸發條件**：LogQL 查詢沒有精確的 label filter、時間範圍 > 24 小時。Loki 要掃描大量 chunks、query timeout（預設 3 分鐘）觸發。

**表現**：Grafana 顯示 query timeout error。

**修法**：查詢時先用 label selector 縮小 stream 範圍（`{job="checkout", namespace="production"}` 而非 `{namespace="production"}`），再用 line filter 進一步篩。如果業務需要長時間範圍的 log analytics，考慮用 LogQL 的 metric aggregation（`rate(...)` / `count_over_time(...)`）替代原始 log 掃描。

### Chunk target size 與 ingestion rate 的關係

`chunk_target_size`（預設 1.5 MB）控制 chunk 的大小。ingestion rate 低的 stream 可能幾個小時才填滿一個 chunk — 這段期間 chunk 停在 ingester memory 裡。大量低 ingestion rate 的 stream（= 高 cardinality label）會讓 ingester 同時持有大量未 flush 的 chunks，佔用記憶體。

修法方向：降低 `chunk_idle_period`（預設 30 分鐘，時間到即使 chunk 未滿也 flush），或減少低 cardinality stream 的數量。

## 容量與成本

Loki 的成本結構跟 Elasticsearch 根本不同：

| 成本項          | Loki                            | Elasticsearch                      |
| --------------- | ------------------------------- | ---------------------------------- |
| 儲存            | Object storage（S3/GCS）— 便宜  | SSD / local disk — 貴              |
| Index           | 小（只索引 labels）             | 大（inverted index + doc values）  |
| 查詢 compute    | 每次查詢 grep chunks — CPU 密集 | 走 index — 相對輕                  |
| 適合的 workload | 高 volume、低 query frequency   | 高 query frequency、需要 full-text |

Loki 在「每天寫 TB 級 log、偶爾查一下」的場景成本遠低於 Elasticsearch。但在「每天查數百次、需要快速 full-text search」的場景，Elasticsearch 的 pre-indexed 查詢效能更好，Loki 每次 grep 的 compute cost 反而更高。

成本治理的判讀：監控 `loki_ingester_bytes_received_total`（ingestion volume）和 `loki_querier_query_duration_seconds`（query cost）。如果 query duration 持續上升，先檢查是 label filter 不夠精確還是 query 時間範圍太大。

## 整合與下一步

- [Grafana Stack 服務頁](/backend/04-observability/vendors/grafana-stack/)：overview 與全棧操作
- [LGTM Stack Operations](../lgtm-stack-operations/)：Loki 在 LGTM 全棧中的部署位置
- [4.12 Audit Log Governance](/backend/04-observability/audit-log-governance/)：Loki 不適合 audit log 的 compliance 查詢（無 immutable storage 保證、無 fine-grained access control）— 合規需求用 BigQuery 或 dedicated audit backend
- [Healthcare 存取追溯案例](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)：分層 retention 在 Loki 用 tenant-level retention policy 實現
- [4.1 Log Schema](/backend/04-observability/log-schema/)：log 欄位設計影響 Loki 的 label 設計與 parser 效率
- [Elasticsearch ILM 與 Log Pipeline](/backend/04-observability/vendors/elastic-stack/ilm-log-pipeline/)：需要 full-text search 時的替代方案
