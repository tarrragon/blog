---
title: "Gaming：高峰流量下的訊號新鮮度與 Cardinality"
date: 2026-05-07
description: "在高峰事件中控制訊號延遲與維度爆炸，維持告警與定位可信度。"
weight: 2
tags: ["backend", "observability", "case-study"]
---

本案例的核心責任是避免高峰流量讓觀測系統本身失真。若訊號延遲與 cardinality 膨脹失控，值班決策會落在過期資料上。

## 業務背景

一個線上多人遊戲平台，日活躍使用者約 50 萬人。每逢賽季開跑或限時活動，同時在線人數在 30 分鐘內從平日基線暴增 8-10 倍，matchmaking 服務的 request rate 從 5k/s 衝到 50k/s，遊戲伺服器同時運行的 match instance 從數千增到數萬。

觀測系統在平日運作良好 — Prometheus 單機 scrape 500 萬 active series、Grafana dashboard 查詢秒級回應、告警在 1 分鐘內觸發。但每次活動開跑時，觀測系統本身開始劣化：dashboard 查詢從秒級變成分鐘級、告警延遲 5 分鐘以上才送到、部分 metric 直接消失。值班工程師在最需要觀測的時刻失去了可信訊號。

## 技術挑戰

### Cardinality 爆炸

平日的 metric label 設計包含 `match_id`、`player_id` 跟 `server_instance`。平日 active series 約 500 萬，活動開跑後 match 跟 player 數量暴增，active series 在 30 分鐘內衝到 2000 萬。Prometheus 的 head block 記憶體從 20 GB 暴增到 80 GB，超過機器 64 GB 上限，觸發 OOM kill。

OOM 後 Prometheus 重啟需要 replay WAL，這段時間（5-15 分鐘）完全沒有 metric。活動最需要觀測的前 30 分鐘，觀測系統反而停擺。

### Scrape freshness 延遲

即使 Prometheus 沒 OOM，大量 target 的 scrape 時間也會拉長。平日每輪 scrape 15 秒完成，活動期間拉長到 60-90 秒。Scrape interval 設定 30 秒時，下一輪 scrape 在上一輪還沒結束時就啟動，造成 sample 丟失跟時間錯位。Dashboard 上看到的數字可能延遲 2-3 分鐘，值班人員基於過期數據做判斷。

### Alert 閾值失真

告警規則基於平日 baseline 設定 — 例如 `error_rate > 1%` 觸發。活動期間的 error rate 波動更大（matchmaking 短暫排隊造成的 timeout 增加是預期行為），平日閾值在活動期間持續觸發 false positive。值班人員開始 ignore alert，真正的問題（伺服器記憶體洩漏）被淹沒在噪音中。

## 解法

### Cardinality guardrail

把高 cardinality label 從 real-time metric 移除。`match_id` 和 `player_id` 不再作為 Prometheus label，改為 log 和 trace 的欄位。Real-time metric 只保留 `region`、`server_pool`、`game_mode` 等低 cardinality 維度。

需要 per-match 或 per-player 分析時，走 log analytics pipeline（非 real-time，延遲 5-10 分鐘可接受）。這讓 Prometheus 的 active series 在活動期間從 2000 萬降到 800 萬，留在單機可承受範圍。

### Pre-aggregation recording rules

為活動期間最常查的 pattern（per-region error rate、matchmaking queue depth、server utilization）建立 recording rules。Recording rules 在 Prometheus server 端預先計算，dashboard 查詢直接讀預計算結果，避免 heavy aggregation query 在活動期間拖慢 Prometheus。

```yaml
# recording rule 示例
groups:
  - name: peak_precompute
    interval: 15s
    rules:
      - record: region:matchmaking_errors:rate5m
        expr: sum(rate(matchmaking_errors_total[5m])) by (region)
```

### Signal tiering

把觀測訊號分成兩層：

| 層級   | 訊號類型                                                      | Pipeline              | Freshness | Cardinality 限制                  |
| ------ | ------------------------------------------------------------- | --------------------- | --------- | --------------------------------- |
| Tier 1 | Golden signals（latency、error rate、throughput、saturation） | Prometheus real-time  | < 30s     | 嚴格（低 cardinality label only） |
| Tier 2 | Debug signals（per-match、per-player、per-request）           | Log + trace analytics | 5-10 min  | 無限制                            |

Tier 1 支撐告警跟即時 dashboard，保證活動期間不劣化。Tier 2 支撐事後分析跟 root cause investigation，接受延遲。

### Dynamic alert threshold

活動期間啟用「高峰模式」alert profile — 調高 error rate 閾值（1% → 5%）、加長 `for:` duration（1m → 5m）、停用已知在活動期間會 false positive 的告警。高峰模式由活動排程系統自動觸發，活動結束後自動切回平日 profile。

## 取捨

| 面向               | 高 cardinality real-time        | 分層治理                           |
| ------------------ | ------------------------------- | ---------------------------------- |
| Debug 即時性       | 高（per-match real-time）       | 低到中（per-match 延遲 5-10 min）  |
| Prometheus 穩定性  | 低（活動期間 OOM 風險）         | 高（active series 可控）           |
| Dashboard 回應速度 | 活動期間劣化                    | 穩定（recording rules 預計算）     |
| 告警可信度         | 低（false positive 淹沒真問題） | 中到高（dynamic threshold 降噪）   |
| 維護複雜度         | 低（一套 pipeline）             | 中（兩套 pipeline + 高峰模式切換） |

分層治理的核心取捨是犧牲 per-match real-time debug 能力，換取觀測系統在高峰期間的穩定。這個取捨在活動場景成立 — 活動期間最需要的是「整體是否健康」的判斷，per-match debug 在事後分析夠用。

## 回寫教材的連結

- [4.7 Cardinality Cost Governance](/backend/04-observability/cardinality-cost-governance/)：cardinality guardrail 的設計原則與偵測機制。
- [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)：scrape freshness、sampling bias 與 signal tiering。
- [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)：real-time vs batch analytics pipeline 的分層設計。
- [4.4 Dashboard Alert](/backend/04-observability/dashboard-alert/)：dynamic alert threshold 與高峰模式切換。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 流量高峰期間 Prometheus 記憶體使用異常增長或觸發 OOM
- Dashboard 在尖峰時段查詢變慢或 timeout，正好是最需要看的時候
- Alert 在活動期間大量觸發但多數是 false positive，值班人員開始 ignore
- `prometheus_tsdb_head_series` 在特定時段突然暴增，結束後回落
- Metric label 中包含高 cardinality identifier（user_id、session_id、request_id）
