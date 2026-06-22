---
title: "4.C11 Uber：M3 大規模 Metrics 平台"
date: 2026-06-22
description: "從散落的 Prometheus 實例到統一 metrics 平台，處理 cardinality 爆炸、長期 retention 與跨叢集查詢的規模化挑戰。"
weight: 11
tags: ["backend", "observability", "case-study", "prometheus", "metrics"]
---

Uber 的 M3 案例揭露了 metrics 系統從「每個團隊各跑一套 Prometheus」到「全公司共用的 metrics 平台」的轉折點。轉折的核心判斷是：當 active series 總量超過單機 Prometheus 的記憶體上限、且多個團隊需要跨叢集查詢時，自建平台層的成本低於持續橫向複製 Prometheus 實例的成本。

## 業務背景

Uber 的服務觀測涵蓋行程追蹤、即時定價、ETA 計算、司機定位、支付結算與推播通知。每個微服務都暴露 Prometheus-compatible metrics，隨著服務數量成長到數千個，寫入速率達到每秒數十億 data points。

早期每個團隊各自部署 Prometheus，各管自己的 retention、scrape config 與 alerting rules。規模小時這個模式運作良好 — 每個 Prometheus 實例只需要處理自己團隊的幾萬到幾十萬 series。但當組織成長到數百個團隊、數千個服務時，散落的 Prometheus 實例帶來三個問題。

## 技術挑戰

### 單機記憶體天花板

Prometheus 的 TSDB 把 active series 放在記憶體的 head block，每個 series 消耗約 3-4 KB（詳見 [Prometheus 容量規劃](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)）。當單一 Prometheus 實例需要 scrape 的 series 超過 1000 萬時，head block 就需要 40+ GB 記憶體。加上 query execution 跟 WAL replay 的暫時開銷，單機很容易 OOM。

團隊的第一反應是按服務拆分多個 Prometheus 實例，但這讓跨服務查詢變得困難 — 要看一條 request 從 gateway 到 payment 的 latency 分布，需要分別查三個 Prometheus 再手動關聯。

### Retention 與長期趨勢

Prometheus 預設 retention 15 天。容量規劃與季度趨勢分析需要 90 天甚至 1 年的歷史資料。把 Prometheus retention 拉長到 90 天，disk 跟 memory 需求同步上升，而且 compaction 效率在資料量大時會下降。

團隊需要的是分層 retention — 近期資料保留全精度、歷史資料做 downsampling 後保留更久。Prometheus 原生不支援 downsampling。

### 高可用與跨叢集查詢

Prometheus 沒有原生 HA — 標準做法是跑兩個 instance scrape 同一批 target，靠下游去重。但兩個 instance 各自獨立儲存，查詢只打一個；instance 故障切換時會有短暫資料缺口。

跨叢集查詢更困難。Prometheus federation 可以做簡單的 metric 聚合，但 federation 本身是 pull-based scrape — federation target 太多或 series 太大時，federation Prometheus 自己也會 OOM。

## 解法：M3 平台

Uber 開發了 M3 — 一個 Prometheus-compatible 的分散式 metrics 平台，由三個核心元件組成。

### M3DB：分散式 time series storage

M3DB 是分散式 TSDB，資料按 namespace 和 shard 分布在多個節點。每個 namespace 可以有不同的 retention 和 resolution — 例如 `realtime` namespace 保留 2 天全精度，`aggregated_1m` namespace 保留 90 天 1 分鐘精度。這解決了 retention tiering 的問題。

M3DB 的記憶體模型跟 Prometheus 不同 — 近期資料在記憶體，冷資料在 disk，不像 Prometheus 把所有 active series 都放 head block。這讓它能處理遠超單機 Prometheus 的 series 數量。

### M3 Coordinator：統一查詢入口

M3 Coordinator 接收 PromQL 查詢，轉譯後分發到 M3DB 節點，聚合結果後返回。對 Grafana 和 alerting rules 來說，M3 Coordinator 的 API 跟 Prometheus 完全相容 — 不需要改 dashboard 或 alert config。

### M3 Aggregator：寫入路徑聚合

高 cardinality 的原始 series 在寫入 M3DB 前先經過 M3 Aggregator 做 pre-aggregation — 例如把每秒的 request count 聚合成每分鐘，再寫入長期 namespace。這控制了長期儲存的資料量跟成本。

## 取捨

| 面向              | Prometheus standalone | M3 平台                               | Mimir / Thanos（替代）        |
| ----------------- | --------------------- | ------------------------------------- | ----------------------------- |
| 部署複雜度        | 低（單一 binary）     | 高（M3DB + Coordinator + Aggregator） | 中到高                        |
| 單機 series 上限  | ~500 萬-1000 萬       | 不適用（分散式）                      | 不適用                        |
| Retention tiering | 無                    | 原生支援                              | Thanos compactor / Mimir 支援 |
| PromQL 相容       | 原生                  | 相容                                  | 相容                          |
| 社群活躍度        | 高（CNCF）            | 低（Uber 主導、2023 後維護縮減）      | 高（Grafana Labs / 社群）     |
| 適用規模          | 單團隊到中型組織      | 大型組織（數十億 series）             | 中型到大型                    |

M3 的最大風險是社群活躍度 — Uber 自 2023 年後縮減了 M3 的開發投入，Grafana Mimir 成為更活躍的替代。新專案選型時，Mimir 跟 Thanos 的社群支援度跟 Grafana 生態整合度都優於 M3。M3 的價值在於它驗證了「分散式 TSDB + 寫入路徑聚合 + retention tiering」這組設計模式，這組模式在 Mimir 跟 Thanos 裡以不同形式被採用。

## 回寫教材的連結

- [4.2 Metrics Basics](/backend/04-observability/metrics-basics/)：active series、cardinality 與 recording rules 的基礎模型，M3 的 pre-aggregation 對應 recording rules 的平台化版本。
- [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)：M3 的 Aggregator 是 pipeline 中 processing 層的實例。
- [Prometheus Remote Write 與長期儲存](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)：M3 是 remote write 目標之一，跟 Mimir / Thanos / Cortex 的比較在該文。
- [4.7 Cardinality 治理](/backend/04-observability/cardinality-cost-governance/)：M3 的 per-namespace cardinality limit 是治理機制的生產實例。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 單一 Prometheus 實例 memory 接近機器上限，開始 OOM restart
- 多個 Prometheus 實例各自 scrape，跨服務查詢需要手動關聯
- Retention 15 天不夠做季度趨勢分析，但拉長 retention 資源撐不住
- 團隊開始問「我們的 metrics 總共有多少 series、誰佔最多」但沒有統一的 cardinality 觀測
- Grafana federation dashboard 查詢越來越慢或經常 timeout

## 引用源

- [M3: Uber's Open Source, Large-scale Metrics Platform for Prometheus](https://www.uber.com/en-GB/blog/m3/)
