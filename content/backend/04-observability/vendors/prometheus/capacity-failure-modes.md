---
title: "Prometheus 容量規劃與故障模式"
date: 2026-06-22
description: "說明 Prometheus 單機容量邊界、cardinality 與 retention 的資源模型、常見故障模式與判讀方式"
weight: 10
tags: ["backend", "observability", "prometheus", "capacity", "failure-mode"]
---

> 本文是 [Prometheus](/backend/04-observability/vendors/prometheus/) 的 vendor deep article，深化 overview「Cardinality 管理」跟「Memory pressure」段。初次接觸 Prometheus 的讀者建議先讀 [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)。

## 定位

Prometheus 的容量模型跟傳統資料庫不同 — 它的容量邊界主要受 active series 數量（cardinality）跟 retention 期決定，而非資料筆數或 disk size。理解 Prometheus 的資源消耗模型，才能判斷什麼時候單機夠用、什麼時候需要 remote write 卸載或遷移到 Mimir / Thanos。

## 資源消耗模型

### Memory：由 active series 決定

Prometheus 把近期的 time series 保存在記憶體（head block）。每個 active series 大約消耗 3-4 KB 記憶體（含 index、chunks、postings；Prometheus TSDB 的業界經驗值，實際依 label 長度與 chunk encoding 而定）。

| Active series | 預估 memory（head block） | 適合的機器規格 |
| ------------- | ------------------------- | -------------- |
| 10 萬         | ~400 MB                   | 任何 VM        |
| 100 萬        | ~4 GB                     | 8 GB VM        |
| 500 萬        | ~20 GB                    | 32 GB VM       |
| 1000 萬       | ~40 GB                    | 64 GB VM       |

這是 head block 的記憶體，不含 query execution 跟 WAL replay 的暫時開銷。Heavy PromQL query（大範圍 aggregation、多 series join）會額外消耗數 GB 的暫時記憶體。

判讀指標：`prometheus_tsdb_head_series` 代表當前 active series 數量，`process_resident_memory_bytes` 代表實際記憶體使用。兩者的比值偏離預期時（例如 50 萬 series 但記憶體用了 10 GB），可能是 query 記憶體壓力或 WAL corruption。

### Disk：由 retention 期與 ingestion rate 決定

Prometheus 的 disk 消耗 = ingestion rate × retention 期 × 壓縮後每 sample 大小（約 1-2 bytes，Gorilla 壓縮算法下的業界經驗值）。

| Ingestion rate    | Retention | 預估 disk |
| ----------------- | --------- | --------- |
| 10 萬 samples/sec | 15 天     | ~130 GB   |
| 10 萬 samples/sec | 30 天     | ~260 GB   |
| 50 萬 samples/sec | 15 天     | ~650 GB   |

Disk I/O 的瓶頸通常在 compaction — Prometheus 定期把 head block 壓縮成 persistent block。Compaction 期間的 disk write 跟 CPU 使用會短暫上升。SSD 環境下 compaction 通常不是問題；HDD 環境下可能造成 scrape timeout。

### CPU：由 scrape 數量與 query 負載決定

Scrape 本身的 CPU 消耗不高（HTTP GET + parse），但 scrape 數量 × scrape 間隔決定了基本的 CPU 基線。1000 個 target × 15 秒間隔 = 每秒 ~67 次 scrape，單核可以處理。

Query 是 CPU 的主要消耗者。Recording rule evaluation、alert rule evaluation、dashboard panel 查詢各自佔 CPU。Recording rule 數量增長到數百條時，evaluation 的 CPU 消耗可能成為瓶頸。

判讀指標：`prometheus_rule_evaluation_duration_seconds` 的 p99 超過 evaluation interval 時，rule 跑不完、alert 會延遲。

## Cardinality 失控的判讀

Cardinality 是 Prometheus 最常見的容量問題。一個意外的高 cardinality label（user_id、request_id、完整 URL）可以在分鐘內把 series 數從 10 萬推到 100 萬、消耗數 GB 記憶體。

### 判讀訊號

- `prometheus_tsdb_head_series` 持續成長、斜率陡峭
- `prometheus_tsdb_head_active_appenders` 成長（新 series 的寫入速率）
- Prometheus 的 memory 持續上升、最終 OOM kill
- Query 延遲增加（更多 series 要掃描）
- Compaction 時間變長

### 定位方式

```text
# 找出哪個 metric name 的 series 最多
topk(10, count by (__name__)({__name__=~".+"}))

# 找出哪個 job（scrape target）的 series 最多
topk(10, count by (job)({__name__=~".+"}))

# 找出某個 metric 的哪個 label 組合在爆
count by (method, status) (http_requests_total)
```

### 修復方向

- **Label 白名單**：在 scrape config 或 relabeling rule 中 drop 高 cardinality label
- **Metric relabeling**：`metric_relabel_configs` 在 scrape 後、寫入前移除特定 label
- **Recording rule 替代**：把高 cardinality metric 聚合成低 cardinality 的 recording rule，下游只讀 recording rule
- **移到 traces**：user_id / request_id 這類維度放在 [trace](/backend/knowledge-cards/trace/) 的 span attribute 而非 metric label

## 常見故障模式

### OOM Kill

**觸發條件**：active series 超過記憶體容量、或 heavy query 消耗大量暫時記憶體。

**表現**：Prometheus process 被 kernel OOM killer 終止。重啟後 WAL replay 可能需要分鐘到十分鐘（取決於 WAL 大小），期間 scrape 跟 query 都不可用。

**預防**：設定 memory limit alert（process_resident_memory_bytes / machine memory > 70%）、tracking cardinality growth slope、query timeout 限制。

### Scrape timeout 連鎖

**觸發條件**：target 的 metrics endpoint 回應慢（> scrape_timeout）、或 target 數量超過 Prometheus 的並行 scrape 能力。

**表現**：`up` metric 為 0、`scrape_duration_seconds` 升高、dashboard 出現資料斷層（missing data points）。大量 target 同時 timeout 時，Prometheus 的 scrape goroutine pool 被佔滿，影響其他健康 target 的 scrape。

**修復**：調整 `scrape_timeout`（預設 10s，太短會造成 false timeout）、把慢 target 移到獨立的 scrape pool、或把 metrics endpoint 的回應最佳化（減少 expose 的 metric 數量）。

### WAL corruption

**觸發條件**：Prometheus process 非正常終止（OOM kill、機器斷電）時，WAL 可能損壞。

**表現**：重啟後 WAL replay 失敗、Prometheus 無法啟動。Error log 顯示 `WAL corrupted` 或 `invalid segment`。

**修復**：刪除損壞的 WAL segment（丟失對應時間段的資料），重啟 Prometheus。嚴重時刪除整個 data 目錄重新開始（丟失所有歷史資料）。WAL 的持久性保證不如資料庫 — Prometheus 設計上允許短暫資料丟失，長期儲存靠 remote write 到 Mimir / Thanos。

### Recording rule evaluation lag

**觸發條件**：recording rule 數量多且表達式複雜、evaluation 時間超過 evaluation interval。

**表現**：`prometheus_rule_group_last_duration_seconds` 超過 `prometheus_rule_group_interval_seconds`。Dashboard 讀 recording rule 的 panel 看到的資料落後當前時間。Alert rule 也在同一個 evaluation pipeline 裡，evaluation lag 會讓 alert 延遲觸發。

**修復**：把重的 recording rule 拆到獨立的 rule group（各自 evaluation interval）、最佳化 PromQL expression（減少 aggregation 層數、縮小 time range）、或把 recording rule 卸載到 Mimir（ruler component 獨立擴展）。

## 何時該從單機 Prometheus 遷出

| 訊號                                                                                           | 下一步                                    |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Active series > 500 萬、memory 吃緊（32 GB VM 上 head block ~20 GB + query overhead 接近上限） | Remote write 到 Mimir / Thanos 做長期儲存 |
| 需要跨 region / cluster 查詢                                                                   | Thanos query 或 Mimir multi-tenant        |
| Recording rule evaluation lag 持續                                                             | 把 rule evaluation 卸載到 Mimir ruler     |
| 需要 HA（single Prometheus = SPOF）                                                            | 兩個 instance + Thanos dedup              |
| Retention 要 > 90 天但 disk 不夠                                                               | Remote write + 短 local retention         |

遷出的第一步通常是加 remote write — Prometheus 繼續本地 scrape 跟短期查詢，長期資料寫到遠端。這是最低風險的演進路徑，不需要改 scrape config 或 PromQL。

## 下一步路由

- [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)：overview 跟日常操作
- [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/)：cardinality 治理的完整策略
- [4.2 metrics basics](/backend/04-observability/metrics-basics/)：recording rule 跟 rollup 的查詢面設計
- [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)：Mimir 作為 Prometheus 的長期儲存後端
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：recording rule 在查詢設計中的定位
