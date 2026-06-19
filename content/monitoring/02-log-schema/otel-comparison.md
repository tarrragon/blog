---
title: "跟 OpenTelemetry 的 schema 差異對照"
date: 2026-06-19
description: "自架 event schema 和 OTLP 的設計差異 — 為什麼 client-side 監控用簡化 schema、什麼時候切換到 OTLP"
weight: 4
tags: ["monitoring", "log-schema", "opentelemetry", "otlp", "comparison"]
---

OpenTelemetry（OTLP）是 server-side 可觀測性的業界標準，定義了 traces、metrics、logs 三種 signal 的資料格式和傳輸協定。自架的 event schema 和 OTLP 在設計目標、複雜度和適用場景上有明確差異。

## 設計目標差異

### OTLP

OTLP 的設計目標是「跨語言、跨框架、跨 vendor 的統一可觀測性標準」。它支援分散式追蹤（trace context propagation）、多維度 metric（histogram、summary、exponential histogram）、結構化 log。

OTLP 的資料模型假設 server-side 的基礎設施：collector（如 OTel Collector）做資料路由和轉換，backend（如 Jaeger、Prometheus、Grafana）做儲存和視覺化。

### 自架 event schema

自架 schema 的設計目標是「client-side 監控的最小可用結構」。它假設的基礎設施是一個 HTTP endpoint + JSONL 檔案 + grep。不需要分散式追蹤（client 端通常是單一服務），不需要多維度 metric（counter 和 gauge 用 event 的 data 欄位表示即可）。

## 具體差異

| 維度          | OTLP                                 | 自架 event schema              |
| ------------- | ------------------------------------ | ------------------------------ |
| Signal 類型   | Trace / Metric / Log 三種獨立 signal | 統一的 event 格式 + type 欄位  |
| 傳輸格式      | Protobuf（HTTP/gRPC）                | JSON（HTTP POST）              |
| Trace context | SpanID / TraceID / ParentSpanID      | Session ID（無分散式追蹤）     |
| Metric 模型   | Sum / Gauge / Histogram / Summary    | data 欄位中的數值              |
| Resource      | 結構化的 resource attributes         | source 欄位                    |
| Schema 複雜度 | 高（完整的 Protobuf 定義）           | 低（JSON Schema，核心 6 欄位） |

## 自架 schema 簡化了什麼

### 不做分散式追蹤

OTLP 的 trace signal 用 TraceID 和 SpanID 把跨服務的請求關聯起來。Client-side 監控通常不需要這個能力 — app 是單一服務，不存在跨服務的請求鏈路。

自架 schema 用 session ID 關聯同一次使用中的事件，滿足「使用者在這次操作中做了什麼」的分析需求。

### 不用 Protobuf

OTLP 用 Protobuf 編碼資料，效率高（binary 格式、schema 驗證在編譯期）。但 Protobuf 需要 schema 檔案（.proto）、程式碼生成、和 SDK 語言的 Protobuf 套件。

自架 schema 用 JSON，人類可讀、grep 友好、不需要額外工具。JSON 的效率比 Protobuf 低（文字格式、體積較大），但在 client-side 監控的事件量下（每分鐘數十到數百筆），效率差異不構成瓶頸。

### 簡化 metric 模型

OTLP 的 metric signal 支援 histogram（分桶分佈）、summary（百分位）、exponential histogram（自適應分桶）。這些模型在 server-side 的高頻度 metric 收集中有意義。

自架 schema 把 metric 記錄為 event 的 data 欄位中的數值（`{"type": "metric", "name": "connect.duration", "data": {"value_ms": 320}}`）。統計分析在 collector 端用查詢完成，不在 schema 層做聚合。

## 什麼時候切換到 OTLP

以下訊號出現時，自架 schema 的簡化可能成為限制：

**需要和 server-side 追蹤關聯**：Client 端的操作要關聯到 server 端的 trace（「使用者點擊按鈕到 database query 的完整路徑」）。需要 OTLP 的 trace context propagation。

**事件量超過 JSONL 的處理能力**：每秒數千筆事件時，JSON 的解析和 JSONL 的 grep 查詢成為瓶頸。OTLP + OTel Collector + 時間序列 DB 的管線能處理更高的吞吐量。

**需要接入多個 backend**：同時送資料到 Prometheus（metric）、Jaeger（trace）、Elasticsearch（log）。OTel Collector 原生支援多 backend 路由，自架方案需要自己實作。

切換策略：SDK 層的 API 不變（init / event / error / metric），只改底層的傳輸和編碼。從 JSON POST 改成 OTLP export，SDK 的使用者不需要改程式碼。

## 下一步路由

- 自架 schema 的完整定義 → [event.schema.json 完整欄位解說](/monitoring/02-log-schema/event-schema-fields/)
- Server-side 的可觀測性 → [backend 04 可觀測性](/backend/04-observability/)
- Collector 的設計 → [模組四 Collector 設計](/monitoring/04-collector/)
