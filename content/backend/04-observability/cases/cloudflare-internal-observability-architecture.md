---
title: "4.C12 Cloudflare：內部觀測平台的三層能力"
date: 2026-06-22
description: "全球 300+ edge 節點的觀測架構，把 monitoring、analytics 與 forensics 拆成三個獨立能力層。"
weight: 12
tags: ["backend", "observability", "case-study", "telemetry-pipeline", "cost"]
---

Cloudflare 的觀測架構把 monitoring、analytics 和 forensics 拆成三層 pipeline，三層各自承擔不同的 resolution、retention 和查詢模式。規模到達每秒數十億 request、300+ edge location 時，用同一套 pipeline 處理三種能力會同時在成本跟查詢延遲上碰壁。

## 業務背景

Cloudflare 的服務涵蓋 CDN、DNS、DDoS 防護、Workers 邊緣運算與 Zero Trust 安全。每秒處理數十億 HTTP request，分布在全球 300+ 資料中心。觀測資料量極大 — 僅 HTTP request log 每秒就產生數百 GB 未壓縮的結構化日誌。

早期觀測用單一 pipeline 處理所有資料，隨著資料量成長，pipeline 面臨三個壓力：monitoring 需要秒級即時性但不需要全量資料；analytics 需要完整資料但可以延遲分鐘級；forensics（鑑識）需要保留原始事件但查詢頻率極低。

## 技術挑戰

### 資料量與成本

每秒數十億 request 的全量日誌，即使壓縮後仍是 PB 級月儲存量。把全量資料送到集中式 log backend（無論是自建 Elasticsearch 或 SaaS Datadog）的 ingestion 成本本身就是天文數字。

Cloudflare 公開表示過去曾用過 Kafka + Elasticsearch + Grafana 的組合，但隨著 edge 節點增加，centralized ingestion 的頻寬跟儲存成本持續超線性成長。

### Edge 到 Core 的延遲

觀測資料從 300+ edge 節點匯聚到中心叢集，網路延遲跟 bandwidth 是物理限制。monitoring 需要秒級判斷（alert 要快觸發），但全量日誌的傳輸延遲可能是分鐘級。

### 查詢模式衝突

on-call 值班需要的是 dashboard 上的 aggregated metrics（error rate、latency percentile、traffic volume），查詢要快、資料要即時。analytics 團隊需要的是全量日誌做 ad-hoc 查詢（某個 IP 在過去 24 小時的 request pattern），查詢可以慢、但資料要完整。forensics 需要的是單一事件的原始內容（某筆 request 的完整 header 跟 body），查詢極少但需要保留數月。

三種查詢模式在 resolution、freshness 跟 retention 上的需求完全不同，用同一套 backend 處理會讓所有人的體驗都變差。

## 解法：三層觀測能力

### Monitoring：pre-aggregated metrics + alerting

edge 節點在本地做 pre-aggregation — 把每秒的 request count、error count、latency histogram 聚合成每 10 秒的 metric batch，push 到中心的 metrics backend。資料量從 PB/月壓縮到 TB/月。

Alerting 跟 dashboard 只看聚合後的 metrics，查詢延遲在毫秒級。metrics backend 用 Prometheus-compatible 儲存，Grafana 作為查詢入口。

### Analytics：sampled + full-fidelity log pipeline

analytics 層接收全量日誌但做分層處理：高流量 endpoint 的日誌做 adaptive sampling（保留 1%-10%），低流量跟異常 request 保留全量。日誌送到自建的 columnar store（Cloudflare 用 ClickHouse 類的 OLAP 引擎），支援 ad-hoc 查詢。

Retention 30-90 天，查詢延遲在秒到分鐘級。成本比 monitoring 層高但仍可控 — sampling 是關鍵的成本旋鈕。

### Forensics：原始事件歸檔

需要完整保留的事件（安全事件、DDoS 攻擊、客戶投訴關聯的 request）寫入冷儲存（object storage）。查詢走 batch 模式（scan-based），延遲在分鐘到小時級。

Retention 按合規需求保留 6 個月到數年。成本主要是儲存（object storage 便宜），ingestion 跟 query 成本極低。

## 取捨

| 面向           | 單一 pipeline                                     | 三層拆分                                                        |
| -------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| 架構複雜度     | 低（一條路走完）                                  | 高（三條路各自維護）                                            |
| 成本可控度     | 差（全量資料走同一條路，成本隨 traffic 線性成長） | 好（每層各自有成本旋鈕）                                        |
| 查詢一致性     | 高（同一個 backend 查）                           | 低（三個 backend，查詢語言可能不同）                            |
| Freshness      | 被最慢的一段拖住                                  | 每層獨立（monitoring 秒級、analytics 分鐘級、forensics 小時級） |
| Debugging 路徑 | 短（一個入口）                                    | 長（先看 monitoring 判斷層級、再決定進 analytics 或 forensics） |

三層拆分的最大風險是 debugging 路徑變長 — on-call 先看 dashboard 發現異常，再到 analytics 查 sampled log 找 pattern，最後到 forensics 查原始事件確認細節。如果三層之間的 correlation ID（trace ID、request ID）沒有對齊，跨層查詢會斷掉。

## 回寫教材的連結

- [4.1 Log Schema](/backend/04-observability/log-schema/)：三層共用的欄位設計（correlation ID、timestamp、service tag）是 log schema 的規模化實例。
- [4.3 Tracing Context](/backend/04-observability/tracing-context/)：跨層 correlation 依賴 trace context propagation，edge → core 的 context 傳遞是挑戰。
- [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)：三層拆分就是 pipeline 的 routing 跟 processing 層設計。
- [4.15 Cost Attribution](/backend/04-observability/cost-attribution/)：三層各自的成本旋鈕（sampling rate、retention、storage tier）是成本歸因的實作入口。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 觀測平台帳單主要被全量日誌 ingestion 佔據，但 90% 的日誌沒人查過
- Dashboard 查詢越來越慢，因為查詢打的是存了全量資料的同一個 backend
- on-call 跟 analytics 團隊對觀測 backend 的需求衝突（一個要快、一個要全）
- edge / CDN / 多 region 架構下，central pipeline 的 ingestion bandwidth 成為瓶頸
- 安全團隊要求保留原始事件 6 個月以上，但 hot tier 儲存成本撐不住

## 引用源

- [Our Vision for Observability at Cloudflare](https://blog.cloudflare.com/vision-for-observability/)
- [Building Cloudflare on Cloudflare](https://blog.cloudflare.com/building-cloudflare-on-cloudflare/)
