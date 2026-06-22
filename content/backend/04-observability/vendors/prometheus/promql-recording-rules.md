---
title: "PromQL 與 Recording Rules 實務"
date: 2026-06-22
description: "說明 PromQL 常見查詢模式、recording rules 設計慣例、SLI 表達式寫法與效能陷阱的判讀方式"
weight: 11
tags: ["backend", "observability", "prometheus", "promql", "recording-rules"]
---

> 本文是 [Prometheus](/backend/04-observability/vendors/prometheus/) 的 vendor deep article，深化 overview「PromQL 查詢」跟「Recording rules / Alerting rules」段。初次接觸 Prometheus 的讀者建議先讀 [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)。

## 問題情境

Recording rules 把昂貴的即時聚合預先計算成低延遲 series，降低 dashboard 查詢成本並穩定 alerting 表達式。三個觸發點會讓團隊需要認真處理 PromQL 與 recording rules：

Grafana dashboard 的某些 panel 載入超過 10 秒。原因通常是 panel 直接查詢高 cardinality 的原始 metric，每次載入都做一次完整的 range query aggregation。Recording rules 預先計算聚合結果，dashboard 只讀計算好的 series，查詢時間從秒級降到毫秒級。

Alert 表達式想表達「最近 5 分鐘的 error rate 超過 1% 且持續 2 分鐘」，但寫出來的 PromQL 要麼漏抓（counter reset 時 rate 歸零）、要麼誤報（absent series 觸發 NaN 比較）。這類問題的根源是對 counter vs gauge 的語意差異理解不夠精確。

Recording rules 堆了上百條但沒有命名慣例，新加的 rule 不確定是否跟既有 rule 重疊、也不確定 evaluation 順序是否正確。缺乏結構化的 rule 管理會讓 rule group 的 evaluation 時間逐漸超過 interval。

## 核心概念

### Counter 與 gauge 的查詢差異

Counter 是單調遞增的累計值（total requests、total bytes sent），只在 process 重啟時 reset。Gauge 是瞬時值（temperature、goroutine count、queue depth），隨時上下波動。

查詢 counter 必須用 `rate()` 或 `increase()` — 直接讀 counter 的原始值沒有業務意義（「從啟動到現在共 5 百萬個 request」不是有用訊號）。`rate()` 回傳每秒平均增量，`increase()` 回傳區間內的總增量。兩者都自動處理 counter reset — 當值突然下降時（process restart），rate 不會回傳負值。

查詢 gauge 直接讀原始值即可，用 `avg_over_time()`、`max_over_time()` 等做區間統計。

常見錯誤是對 gauge 用 rate（結果無意義 — 溫度的「每秒變化率」不是有用訊號）、或對 counter 直接取 max_over_time（只拿到 counter 的最大累計值、不是最大 QPS）。

### rate 與 increase 的差異

`rate(http_requests_total[5m])` 回傳 5 分鐘內的平均每秒 request 數。`increase(http_requests_total[5m])` 回傳 5 分鐘內的總增量，等於 `rate() * 300`。

選擇取決於讀者的心智模型：SLI dashboard 用 rate（「每秒多少」直觀）；報表用 increase（「過去一小時多少筆」直觀）。

Range 的選擇有一個實務邊界：range 至少要涵蓋 2 個 scrape interval。15 秒 scrape interval 搭配 `rate(...[30s])` 是最小可用 range；`rate(...[15s])` 可能只抓到一個 sample，回傳 NaN。production 常用 `[5m]` 作為預設 range — 足夠平滑短暫抖動、又不會過度延遲異常偵測。

### histogram_quantile 的 bucket 設計

Prometheus histogram 使用預定義 bucket 邊界收集觀測值分布。`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` 計算 p95 延遲。

Bucket 邊界的設計直接影響精確度。預設 bucket（0.005, 0.01, 0.025, ... 10）適合 HTTP request 延遲場景。如果服務的 p50 在 200ms 而 bucket 只有 0.1 跟 0.25 兩個相鄰邊界，p50 的計算會在 100ms-250ms 之間做線性內插，精確度受限。

設計 bucket 的判準：p50 和 p99 附近各要有 2-3 個相鄰 bucket，讓內插結果接近真實值。SLO 的 latency threshold 也應該落在某個 bucket 邊界上 — 例如 SLO 是 p95 < 500ms，那 500ms 應該是一個 bucket 邊界。

每個 bucket 是一個 time series。10 個 bucket 的 histogram + 4 個 label 組合 = 40 個 series。Bucket 數量增加到 30 個時，同一個 metric 的 series 數量膨脹 3 倍。Bucket 設計要在精確度與 cardinality 之間取捨。

### Label matching 規則

PromQL 的 binary operation（`/`、`+`、comparison）預設要求兩邊的 label set 完全一致才做 matching。這會在 error rate 計算時造成問題：`rate(http_requests_total{status=~"5.."}[5m])` 的 label set 含 status、但 `rate(http_requests_total[5m])` 的 total 不含 status。

解法是在分子做 aggregation 時 drop 掉 status label：

```promql
sum by (job, method) (rate(http_requests_total{status=~"5.."}[5m]))
/
sum by (job, method) (rate(http_requests_total[5m]))
```

`on()` 和 `ignoring()` 修飾符可以在不做 aggregation 的前提下控制 matching，但可讀性較差。production 推薦的做法是先用 `sum by()` 控制輸出的 label set，讓兩邊的 label 對齊。

## 配置：常見 SLI Pattern

### Error rate

```yaml
# recording rule: 每 5 分鐘計算一次 error rate
groups:
  - name: sli_error_rate
    interval: 30s
    rules:
      - record: job:http_request_error_rate:ratio_rate5m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum by (job) (rate(http_requests_total[5m]))
```

命名慣例 `level:metric:operations` 來自 Prometheus 官方建議：`job` 是聚合的 level、`http_request_error_rate` 是語意、`ratio_rate5m` 是操作。遵循慣例讓團隊成員看到 rule 名稱就知道它的聚合粒度與計算方式。

### Latency percentile

```yaml
      - record: job:http_request_duration_seconds:p95_rate5m
        expr: |
          histogram_quantile(0.95,
            sum by (job, le) (rate(http_request_duration_seconds_bucket[5m]))
          )
```

`le` label 是 histogram bucket 邊界，`sum by (job, le)` 把 instance 維度聚合掉、保留 bucket 結構。如果漏掉 `le`，`histogram_quantile` 會回傳錯誤結果。

### Throughput

```yaml
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))
```

三個 SLI — error rate、latency、throughput — 組成服務的 [RED metrics](/backend/knowledge-cards/metrics/)（Rate、Errors、Duration）。Recording rules 預先計算後，dashboard 只需讀三個 series。

### Alerting rule 搭配 recording rule

```yaml
  - name: sli_alerts
    rules:
      - alert: HighErrorRate
        expr: job:http_request_error_rate:ratio_rate5m > 0.01
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "{{ $labels.job }} error rate above 1% for 5 minutes"
```

Alert 表達式讀 recording rule 而非原始 metric。好處有二：alert evaluation 更快（讀預先計算的 series）、alert 表達式與 dashboard panel 使用同一組 recording rule（確保看到的數字一致）。

## 故障與邊界

### Series churn 導致 absent() 判斷失準

`absent(up{job="myapp"})` 用來偵測 target 完全消失（沒在 scrape）。但在 K8s 環境，pod 頻繁 rolling update 會造成 series churn — 舊 pod 的 series 消失、新 pod 的 series 出現。短暫的時間窗內 `absent()` 可能誤觸。

修法：用 `absent_over_time(up{job="myapp"}[5m])` 替代，要求整個 5 分鐘區間都沒有 series 才觸發。或用 `count(up{job="myapp"}) == 0` 明確檢查 series 數量。

### Recording rules circular dependency

Rule group A 的 rule 讀 rule group B 的 recording rule、group B 又讀 group A 的結果。Prometheus 按 group name 字母序 evaluate，circular dependency 會讓一方讀到上一輪的 stale 結果。

預防方式：recording rules 形成 DAG（有向無環圖）。Prometheus 文件建議把 rule 分成 aggregation 層級 — 底層 group 算 raw metric 的 aggregation、上層 group 算 recording rule 的 aggregation。同一個 group 內的 rule 按宣告順序同步 evaluate。

### 大 range query OOM

Dashboard panel 用 `rate(metric[30d])` 查詢 30 天 range — Prometheus 要載入 30 天的 samples 到記憶體做計算。100 萬 series × 30 天 × 15 秒 interval ≈ 1.7 億 samples per series 是不可能完成的查詢。

修法：長時間 range 必須用 recording rules 做 step-down aggregation。先用 `rate(...[5m])` recording rule 每 30 秒算一次、再用 `avg_over_time(recording_rule[30d])` 查詢。Recording rule 的 series 數量通常比原始 metric 少一到兩個數量級。

Prometheus 2.x 支援 `--query.max-samples` flag 限制單一 query 能處理的 sample 數量（預設 5000 萬），超過就回傳 error。這是 OOM 的最後防線、不是常態。

### Counter reset 導致 rate 異常

Process 重啟時 counter 歸零。`rate()` 和 `increase()` 自動偵測 counter reset 並補償，但有邊界條件：如果 scrape interval 內發生多次 restart（例如 crash loop），`rate()` 可能低估真實值（只能偵測到一次 reset）。

這種情境下的判讀：如果 `rate()` 的結果明顯低於預期、且同時段有 pod restart 紀錄，rate 低估是正常的。修法是解決 crash loop 本身、而非調整 PromQL。

## 容量與 Cost

Recording rules 的 CPU 成本 = rule 數量 × 每條 rule 的 evaluation 時間 × (1 / evaluation interval)。

| Rule 數量 | 平均 evaluation 時間 | Interval | 每秒 evaluation 消耗        |
| --------- | -------------------- | -------- | --------------------------- |
| 50        | 10ms                 | 30s      | 50 × 0.01 / 30 = 0.017 core |
| 200       | 50ms                 | 30s      | 200 × 0.05 / 30 = 0.33 core |
| 500       | 100ms                | 15s      | 500 × 0.1 / 15 = 3.33 core  |

表中的 evaluation 時間是 10 萬到 50 萬 active series 規模下的經驗值。Series 數量影響 evaluation 時間 — 100 萬 series 的 complex aggregation 可能 500ms+，跟表中假設偏差很大。用 `prometheus_rule_group_last_duration_seconds` 量測自己環境的實際值。

500 條 complex rule 搭配 15 秒 interval 會消耗超過 3 個 CPU core 在 rule evaluation 上。這時候的修法方向有三：

- 把 evaluation interval 放寬到 30s 或 60s（犧牲即時性）
- 把 rule 表達式最佳化（減少 aggregation 層數）
- 把 rule evaluation 卸載到 Mimir ruler（水平擴展）

Recording rules 產生的新 series 也會增加 cardinality。200 條 recording rule × 平均 5 個 label 組合 = 1000 個新 series，通常可接受。但如果 recording rule 沒做 aggregation 而是直接 alias（`record: new_name expr: old_metric`），cardinality 不會減少，只增加了寫入成本。

判讀指標：`prometheus_rule_group_last_duration_seconds` 跟 `prometheus_rule_group_interval_seconds` 的比值。前者超過後者時，evaluation 跑不完、dashboard 跟 alert 都會延遲。見 [容量規劃與故障模式](../capacity-failure-modes/) 的 Recording rule evaluation lag 段。

### Recording rules 作為成本控制工具

[觀測成本治理案例](/backend/04-observability/cases/observability-cost-governance-at-scale/)提出一個被低估的用法：recording rules 不只是加速查詢、也是控制 remote write 成本的手段。

模式是這樣的：application 暴露 200 個 label 組合的原始 metric（per-endpoint × per-status × per-region），recording rule 聚合成 5 個 label 組合（per-service × per-region）。如果 remote write 設定了 `write_relabel_configs` drop 掉原始 series、只 forward recording rule 產生的 aggregated series，remote write bandwidth 跟長期儲存的 cardinality 都大幅降低。

```yaml
# Step 1: recording rule 做 aggregation
groups:
  - name: cost_optimized
    rules:
      - record: service_region:http_requests:rate5m
        expr: sum by (service, region) (rate(http_requests_total[5m]))

# Step 2: remote write 只送 aggregated series
remote_write:
  - url: "http://mimir:9009/api/v1/push"
    write_relabel_configs:
      - source_labels: [__name__]
        regex: "service_region:.*"
        action: keep
```

這個模式的取捨：長期儲存只有 aggregated 資料、無法回溯到原始 per-endpoint 維度。如果事故時需要 per-endpoint 的歷史資料，要麼保留原始 series 在本地 Prometheus（短期 retention）、要麼接受長期儲存只有 aggregated 粒度。

適用場景判斷：如果 dashboard 跟 alert 都只看 service-level 聚合、per-endpoint 維度只在即時除錯時才需要（Prometheus 本地 15 天 retention 夠用），這個模式的成本節省值得。如果有合規需求要 per-endpoint 歷史資料（例如 [FinTech 案例](/backend/04-observability/cases/fintech-audit-evidence-observability/) 的 evidence chain），就不能 drop 原始 series。

### Evaluation interval 對 CPU 的影響

Rule group 的 `interval` 決定 evaluation 頻率。同一組 rules 從 30s interval 改成 15s interval，CPU 消耗翻倍。從 30s 改成 60s，CPU 減半但 alert 跟 dashboard 的即時性下降。

經驗值：

| 場景                             | 建議 interval | 理由                                                                  |
| -------------------------------- | ------------- | --------------------------------------------------------------------- |
| SLI / SLO recording rules        | 30s           | 平衡即時性跟成本、多數 burn rate alert 的最小 window 是 5 分鐘        |
| Capacity trending rules          | 60s-120s      | 趨勢不需要秒級即時性                                                  |
| High-frequency operational rules | 15s           | 需要跟 scrape interval 對齊的場景（例如 real-time anomaly detection） |

15 秒 interval 的 rule group 要特別注意 evaluation 時間 — 如果 evaluation 本身花 12 秒，只剩 3 秒 buffer。`prometheus_rule_group_last_duration_seconds` 持續接近 `prometheus_rule_group_interval_seconds` 時，要麼拆 rule group 到不同 Prometheus instance、要麼放寬 interval。

## 整合與下一步

### Alertmanager

Alert rule 寫在 Prometheus 的 `rule_files` 內、觸發後送到 Alertmanager。Alertmanager 負責去重、分組、抑制與路由（route to PagerDuty / Slack / email）。Alert rule 的表達式跟 recording rule 共用同一組語意 — 讀 recording rule 而非原始 metric。

### Grafana dashboard

Grafana 的 Prometheus datasource 直接查 PromQL。Dashboard panel 推薦讀 recording rule series 而非寫 raw PromQL — 減少 dashboard 載入時間、確保 dashboard 跟 alert 看到的數字一致。

### 對齊 SLI/SLO

Recording rules 產生的 SLI metrics 是 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/) 的資料來源。SLO burn rate alert 也讀同一組 recording rule。確保 SLI recording rule 的 time window 跟 SLO window 對齊（例如 SLO 用 30 天 rolling window，recording rule 至少提供 5m 和 1h 兩個 aggregation 粒度給 burn rate 計算）。

## 交接路由

- [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)：overview 跟日常操作入口
- [容量規劃與故障模式](../capacity-failure-modes/)：recording rules 成長後的資源衝擊
- [Remote Write 與長期儲存整合](../remote-write-long-term-storage/)：recording rule 在 remote write 架構下的部署選擇
- [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)：recording rules 如何餵給 SLO burn rate
- [4.7 Cardinality 治理](/backend/04-observability/cardinality-cost-governance/)：recording rules 作為 cardinality 減量手段
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：recording rules 在 pre-aggregation 與 query tiering 中的定位
