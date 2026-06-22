---
title: "監控資料的雙重用途：行為分析與訊號治理"
date: 2026-06-22
description: "同一份 event data 如何同時服務行為分析（funnel / cohort / attribution）和訊號治理（cardinality / cost / signal governance）— 格式交叉、治理衝突與分流架構"
weight: 50
tags: ["monitoring", "observability", "data-flow", "cross-module"]
---

SDK 埋的每一筆 event 有兩個下游消費者：產品團隊用它做行為分析（轉換率、留存、歸因），工程團隊用它做訊號治理（cardinality 控制、成本歸因、事故判讀）。兩邊各自有教學章節（[Monitoring 08 Business Analytics](/monitoring/08-business-analytics/) 和 [Backend 04 可觀測性](/backend/04-observability/)），但讀者常不知道這是同一份資料的兩種消費方式。本文是橋。

## 同一份資料、兩種消費路徑

```text
SDK 埋點（event / error / metric / lifecycle）
  │
  ├── 行為分析路徑 → Monitoring 08
  │     消費者：PM / 行銷 / 產品
  │     方法：funnel / cohort / attribution / A-B test
  │     決策：改 UI、調定價、投廣告
  │
  └── 訊號治理路徑 → Backend 04
        消費者：SRE / platform team / on-call
        方法：cardinality budget / cost attribution / signal governance
        決策：降 cardinality、調 sampling、改 alert、產出 evidence
```

這不是兩套埋點。同一個 `button.click` event，產品團隊看的是「哪個步驟流失最多使用者」，工程團隊看的是「這個 event 的 cardinality 是否在預算內、ingestion cost 是否合理」。event 相同，切入角度不同。

## 資料格式的交叉點

Monitoring SDK 送出的事件格式（[02 Log Schema](/monitoring/02-log-schema/)）和 Backend 04 的 log schema / OTel event format 有共通欄位：

| 欄位          | Monitoring SDK 格式                             | Backend 04 / OTel 格式      | 交叉用途                                                         |
| ------------- | ----------------------------------------------- | --------------------------- | ---------------------------------------------------------------- |
| timestamp     | `timestamp`（ISO 8601）                         | `TimeUnixNano`              | 兩邊都需要精確時間做時序查詢                                     |
| event type    | `type`（event/error/metric/lifecycle）          | `SeverityText` / `SpanKind` | 行為分析按 type 做 funnel；訊號治理按 type 做 cardinality budget |
| source        | `source.sdk` / `source.platform` / `source.app` | `Resource` attributes       | 行為分析按 platform 切分；訊號治理按 service 做 cost attribution |
| trace context | 手動注入（若有）                                | `TraceId` / `SpanId`        | client-to-server 端到端追蹤的串接欄位                            |
| payload       | `data`（自由 JSON）                             | `Attributes` / `Body`       | 行為分析讀 business fields；訊號治理讀 operational fields        |

格式一致性的價值是**一份 event 同時餵 BigQuery（行為分析）和 Grafana Loki（訊號查詢）不需要格式轉換**。如果兩邊各自定義 schema，同一個 event 要寫兩次 adapter，schema drift 的風險倍增。

## 資料治理的衝突

同一份資料被兩邊消費時，治理需求會衝突：

| 面向     | 行為分析需要                                    | 訊號治理需要                                    | 衝突點                       |
| -------- | ----------------------------------------------- | ----------------------------------------------- | ---------------------------- |
| 保留期   | 長期保留（年級，趨勢與 cohort 需要歷史資料）    | 短期保留（30-90 天，debug 用完即丟）            | 成本 vs 分析完整度           |
| 粒度     | 高粒度（per-user、per-session、per-action）     | 低粒度（聚合到 service / endpoint 維度）        | cardinality 爆炸 vs 分析精度 |
| PII 處理 | 去識別但需保留 user segment（國家、裝置、方案） | 完全匿名或 redacted                             | 分析需求 vs 合規要求         |
| 取樣     | 低取樣或全量（行為趨勢需要完整分布）            | 可以高取樣（error 全收，正常 request 取樣即可） | 成本 vs 覆蓋度               |
| 查詢延遲 | 可接受分鐘級（batch analytics）                 | 需要秒級（incident debug 不能等）               | 儲存分層與查詢 backend 選擇  |

這些衝突無法靠「選一邊」解決。行為分析少了歷史資料就看不到趨勢；訊號治理存太多高粒度資料就 cardinality 爆炸。解法是分流。

## 解法：在 transport 層分流

把 SDK 送出的 event 在 collector 或 pipeline 層分流到不同 backend，各自按需求治理：

### Hot path：即時訊號

error 和 metric 類事件即時進入 [04 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)（Loki / Prometheus / Tempo），短期 retention（30-90 天），服務 on-call debug 和 incident triage。這條路徑要求秒級延遲、低 cardinality（聚合維度）。

### Warm path：行為分析

全部四類事件進入 data warehouse（BigQuery / ClickHouse / Snowflake），長期 retention（年級），服務 funnel、cohort、attribution 和 A/B test。這條路徑接受分鐘級延遲、高粒度（per-user / per-session）。

### Cold path：合規留存

audit-level event 進入 archive storage（Cloud Storage / S3 / Glacier），法規要求的年級保留（GDPR 刪除請求、HIPAA 6 年、金融業更長）。這條路徑寫入後幾乎不查詢，查詢時接受小時級延遲。

### 分流的關鍵設計

分流在 transport 層做，不在 SDK 層做。SDK 統一送出全部 event 到同一個 endpoint，pipeline 按 event type / source / tag 路由到不同 backend。

```text
SDK → Collector / OTel Collector / Cloud Logging
         │
         ├─ [type=error OR type=metric] → Hot path (Loki / Prometheus)
         ├─ [all events]                → Warm path (BigQuery)
         └─ [audit=true]               → Cold path (Cloud Storage)
```

SDK 不需要知道下游有幾個消費者。新增一個消費者（例如新的分析平台）只要在 pipeline 加一條路由，不用改 SDK。

## 實作考量

分流的實作方式取決於 pipeline 架構：

| 架構                                                         | 分流機制                                                         | 適用場景            |
| ------------------------------------------------------------ | ---------------------------------------------------------------- | ------------------- |
| 自架 collector（[Monitoring 04](/monitoring/04-collector/)） | Rule engine 按 event type 寫不同 output file / HTTP endpoint     | 小規模、自用場景    |
| OTel Collector                                               | Processor + 多個 Exporter 組成 pipeline fan-out                  | 中規模、已採用 OTel |
| Cloud Logging（GCP）                                         | Subscription filter + Sink（BigQuery / Cloud Storage / Pub/Sub） | GCP 生態            |
| Kinesis / Firehose（AWS）                                    | Firehose delivery stream + Lambda transform                      | AWS 生態            |

不論哪種架構，分流後的每條 path 要各自設定 retention、sampling、PII handling 和 cost budget。Hot path 的 [cardinality 治理](/backend/04-observability/cardinality-cost-governance/) 規則不該影響 warm path 的分析粒度；warm path 的長期保留成本不該擠壓 hot path 的 freshness。

## 常見誤區

### 用兩套 SDK 替代分流

在 client 端同時整合行為分析 SDK（Mixpanel）和 error tracking SDK（Sentry），看似分工清楚，實際是兩套 schema、兩份 ingestion cost、兩組 PII 風險面、兩套 consent 管理。同一個 user action 在兩個平台各記一次，但欄位名、timestamp 精度、user identifier 可能不同，跨平台 correlation 困難。

統一 SDK + pipeline 分流的成本通常低於雙 SDK 的整合與治理成本。

### Hot path 存全量高粒度

把 per-user / per-session 的完整事件直接灌進 Prometheus 或 Loki，會導致 cardinality 爆炸（[4.7 Cardinality 治理](/backend/04-observability/cardinality-cost-governance/)）。Hot path 的正確做法是在 pipeline 層做 aggregation 或 relabeling，只保留 service / endpoint / status 等低 cardinality 維度。高粒度資料走 warm path。

### Warm path 不做 PII 處理

行為分析需要 user segment，但不需要 PII 原文。warm path 的 ingestion pipeline 應該在寫入 warehouse 前做 PII redaction（hash user_id、truncate IP、strip email）。[Monitoring 07 去識別化](/monitoring/07-security-privacy/) 的策略同時適用於 hot 和 warm path。

## 讀者路由

| 如果你想                             | 先讀                                                                                                                                                        |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 理解 event 格式設計                  | [Monitoring 02 Log Schema](/monitoring/02-log-schema/)                                                                                                      |
| 理解行為分析方法                     | [Monitoring 08 Business Analytics](/monitoring/08-business-analytics/)                                                                                      |
| 理解訊號治理和成本控制               | [Backend 04 Cardinality 治理](/backend/04-observability/cardinality-cost-governance/)、[4.15 Cost Attribution](/backend/04-observability/cost-attribution/) |
| 理解 pipeline 分流架構               | [Backend 04 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)                                                                              |
| 理解 PII 去識別化                    | [Monitoring 07 Security Privacy](/monitoring/07-security-privacy/)                                                                                          |
| 理解 client-to-server 端到端觀測串接 | [Backend 04 Client-to-Server 觀測串接](/backend/04-observability/client-server-trace-integration/)                                                          |
