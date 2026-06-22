---
title: "Datadog 成本治理與 Agent 配置"
date: 2026-06-22
description: "說明 Datadog 的計價模型、custom metrics 成本控制、Agent 部署配置與常見故障模式"
weight: 10
tags: ["backend", "observability", "datadog", "cost", "agent"]
---

> 本文是 [Datadog](/backend/04-observability/vendors/datadog/) 的 vendor deep article，深化 overview 的成本跟 Agent 段。初次接觸 Datadog 的讀者建議先讀 [Datadog 服務頁](/backend/04-observability/vendors/datadog/)。

## 定位

Datadog 是全託管觀測平台，涵蓋 metrics、logs、traces、profiling、RUM、synthetic monitoring。託管方案的核心取捨是「零運維但成本跟用量成正比」— 用得越多付得越多，而且計價維度多（host、custom metric、log ingestion、span、indexed span），成本治理需要理解每個維度的計價模型。

## 計價模型概覽

Datadog 的主要計價維度：

| 維度                    | 計價方式                     | 常見失控來源                      |
| ----------------------- | ---------------------------- | --------------------------------- |
| Infrastructure host     | 每 host/月                   | Auto-scaling 造成 host 數量波動   |
| Custom metrics          | 每 unique time series/月     | Label 爆炸（同 cardinality 問題） |
| Log ingestion           | 每 GB ingested/月            | Debug log level 忘記關            |
| Log indexed retention   | 每 million events × 天/月    | 預設 retention 太長               |
| APM host + indexed span | 每 host/月 + 每 million span | Sampling 沒設、全收               |
| Profiling               | 每 host/月（APM 加購）       | 整體成本疊加                      |

多數 Datadog 成本失控的根因是 custom metrics 跟 log ingestion — 兩者跟 cardinality 跟 log volume 直接相關，成長可以很快。

## Custom Metrics 成本控制

### 什麼算 custom metric

Datadog 把每個 unique 的 metric name + tag 組合算一個 time series。`http_requests_total{service=checkout, method=GET, status=200}` 跟 `http_requests_total{service=checkout, method=POST, status=500}` 是兩個 time series。

Tag 的笛卡爾積決定 series 數量。5 個 service × 4 個 method × 5 個 status = 100 個 series。加一個 `region` tag（3 個值）就變 300 個。加一個 `endpoint` tag（50 個 normalized path）就變 15,000 個。

### 控制策略

**Tag 白名單**：跟 Prometheus 的 label 白名單邏輯相同。只保留有查詢價值的 tag — service、method、status_class（2xx/4xx/5xx）。移除 user_id、request_id、完整 URL。

**Metrics without Limits**：Datadog 的功能 — 在 ingestion 之後、query 之前過濾 tag。所有 tag 都收但只 index / 計費特定 tag。適合「收全量但只查部分維度」的場景。

**DogStatsD 聚合**：Datadog Agent 的 DogStatsD 端在 Agent 層做 pre-aggregation，把客戶端的 per-request metric 聚合成 per-interval 的摘要。減少送到 Datadog 的 data point 數量。DogStatsD 聚合在 Agent 端執行，跟 TSDB 層的 [recording rule](/backend/knowledge-cards/recording-rule/) 是不同位置的 pre-aggregation 機制。

**Usage attribution**：Datadog 的 [Usage Attribution](https://docs.datadoghq.com/account_management/billing/usage_attribution/) 功能把 custom metric 成本拆到 service / team tag，讓團隊看到自己的 metric 成本。對應 [4.15 cost attribution](/backend/04-observability/cost-attribution/)。

### 判讀指標

Datadog UI 的 Metric Summary 頁面顯示每個 metric name 的 tag cardinality。定期（每月）檢查 top 20 高 cardinality metric，確認是否有意外的 tag 爆炸。

## Log Ingestion 成本控制

### Index 策略

Datadog log 的計費分兩層：ingestion（進來就計費）跟 indexing（索引後按保留天數計費）。可以 ingest 所有 log 但只 index 部分 — 非 indexed 的 log 可以在 15 分鐘的 live tail 窗口查看，之後就看不到了（除非歸檔到 S3/GCS 做 rehydrate）。

可操作的分層：

- **Error / warning log**：index，retention 30 天
- **Info log（關鍵路徑）**：index，retention 7 天
- **Debug log**：不 index、只 ingest（live tail 用）；或直接不送
- **Access log（高量）**：不 index、歸檔到 S3、需要時 rehydrate

### Exclusion filter

Datadog 的 index exclusion filter 讓特定 pattern 的 log 進入 ingestion pipeline 但跳過 index。例：health check 的 access log（`path:/health`）每秒數百筆但沒有 debug 價值，設 exclusion filter 讓它不佔 index quota。

### Log pipeline 跟 Datadog log 的對應

[4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 的 collector 端可以在 log 送到 Datadog 之前做 filtering — 低價值 log 直接 drop、不進 Datadog ingestion（連 ingestion 費用都省）。這比 Datadog 的 exclusion filter 更節省成本（exclusion filter 仍然計 ingestion 費用）。

## Agent 部署配置

### Agent 部署模式

| 模式            | 部署位置                 | 適用場景                  |
| --------------- | ------------------------ | ------------------------- |
| Host agent      | 每台 VM 一個 agent       | 傳統 VM 部署              |
| DaemonSet agent | K8s 每個 node 一個 agent | K8s 標準部署              |
| Sidecar agent   | 每個 pod 一個 agent      | 需要嚴格隔離時            |
| Cluster agent   | K8s cluster 一個         | 收集 cluster-level metric |

多數 K8s 部署用 DaemonSet + Cluster Agent 組合。DaemonSet agent 收集 node-level 跟 pod-level 的 metric / log / trace；Cluster Agent 收集 cluster-level 的 metadata 跟 event。

### Agent 健康判讀

Agent 本身需要被監控 — Agent 故障時 Datadog 看到的是「資料消失」而非「Agent 掛了」。

判讀指標（Agent 自帶）：

- `datadog.agent.running`：Agent process 是否存活
- `datadog.agent.check_run`：各 integration check 是否正常
- `datadog.dogstatsd.packets.dropped`：DogStatsD buffer 滿時丟棄的封包數

Agent 掛掉時 dashboard 會出現 gap（資料斷層）。如果所有 host 同時斷層、問題在 Datadog backend；如果特定 host 斷層、問題在該 host 的 Agent。

### 常見 Agent 故障

**CPU / memory over-consumption**：Agent 開太多 integration check 或 DogStatsD 收太多 custom metric。修復：減少 check 數量、調整 DogStatsD 的 aggregation interval、或升級 Agent 版本（新版通常更節省資源）。

**Log collection 延遲**：Agent 的 log tail 落後，log 到達 Datadog 的延遲增加。原因通常是 log rotation 設定跟 Agent 的 tail 設定不一致，或 log 量突然爆增超過 Agent 的處理能力。

**Network connectivity**：Agent 到 Datadog intake endpoint 的網路問題。Agent 會 buffer 資料並重試，但 buffer 滿（預設 100MB）後會 drop。在網路不穩的環境（edge location、受限網路），需要加大 buffer 或設定 proxy。

## 跟 OTel 的整合

Datadog 支援 OpenTelemetry — 可以用 OTel SDK instrumentation + OTel Collector，把資料送到 Datadog backend。這種模式讓 instrumentation 跟 vendor 解耦，但犧牲部分 Datadog-native 功能（例如 Watchdog anomaly detection 需要 Datadog Agent 的 metadata）。

整合模式的選擇跟 [4.C7 Datadog OTel migration practice](/backend/04-observability/cases/datadog-otel-migration-practice/) 的案例分析對應 — 雙軌期的成本跟語意對齊是主要挑戰。

## 下一步路由

- [Datadog 服務頁](/backend/04-observability/vendors/datadog/)：overview 跟日常操作
- [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/)：cardinality 治理的完整策略
- [4.15 cost attribution](/backend/04-observability/cost-attribution/)：成本歸因的組織治理
- [4.C7 Datadog OTel migration](/backend/04-observability/cases/datadog-otel-migration-practice/)：Datadog 跟 OTel 的整合案例
- [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)：vendor-neutral instrumentation
