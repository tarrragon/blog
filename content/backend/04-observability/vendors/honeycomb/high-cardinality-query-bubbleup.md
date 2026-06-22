---
title: "High-Cardinality Query Model 與 BubbleUp"
date: 2026-06-22
description: "說明 Honeycomb 的 event-based 資料模型、high-cardinality 查詢設計、BubbleUp 異常偵測、SLO / burn rate、derived columns、dataset 設計與 OTLP ingestion"
weight: 10
tags: ["backend", "observability", "honeycomb", "high-cardinality", "bubbleup"]
---

> 本文是 [Honeycomb](/backend/04-observability/vendors/honeycomb/) 的 vendor deep article，深化 overview「BubbleUp 分析」跟「Events vs metrics 心智模型」段。初次接觸 Honeycomb 的讀者建議先讀 [Honeycomb 服務頁](/backend/04-observability/vendors/honeycomb/)。

## 問題情境

Metrics-based 觀測系統有一個結構性限制：metric 在寫入前就做了 aggregation，之後只能沿著預先定義的 label 維度查詢。當事故需要按 user_id、request_id、feature_flag_variant 或 deployment_version 定位時，metrics 系統要嘛沒有這些維度（label cardinality 會爆），要嘛需要事先知道要看哪個維度（但事故通常是 unknown-unknowns）。

Honeycomb 用 event-based 模型解決這個問題 — 每一筆 event（通常是一個 trace span）帶幾十個 attribute，查詢時才決定 group by 哪些維度。BubbleUp 進一步自動找出區隔 outlier 跟 baseline 的 attribute，讓工程師不需要事先猜測問題維度。

理解 Honeycomb 的資料模型、查詢設計跟 BubbleUp 的工作方式，才能判斷什麼場景下 Honeycomb 比 metrics-first 系統更有效、什麼場景下 metrics-first 仍然是對的選擇。

## 核心概念

### Event-based 資料模型

Honeycomb 的儲存引擎是 column store — 每一筆 event 是一列、每一個 attribute 是一欄。寫入時不做 aggregation，查詢時才 group by / filter / aggregate。

跟 metrics-first 系統的根本差異：

| 面向        | Metrics-first（Prometheus）            | Event-based（Honeycomb）       |
| ----------- | -------------------------------------- | ------------------------------ |
| 寫入時      | 按 label 組合 aggregate 成 time series | 存原始 event、帶所有 attribute |
| 查詢時      | 只能沿既有 label 維度查詢              | 任意 attribute 組合 group by   |
| Cardinality | label 組合數 = time series 數、有上限  | Attribute 組合數不影響儲存結構 |
| 成本模型    | 按 time series 數計費                  | 按 events volume 計費          |
| 適合        | 已知維度的趨勢監控                     | unknown-unknowns 的事故偵錯    |

一筆 checkout event 在 Honeycomb 可能帶 30+ 個 attribute：service.name、http.method、http.status_code、http.url、user_id、tenant_id、region、deployment_version、feature_flag.variant、db.duration_ms、cache.hit、payment.provider、error.message 等。在 Prometheus 上，user_id 跟 tenant_id 是不能當 label 的（cardinality 爆）；在 Honeycomb 上，它們只是多一欄。

### BubbleUp 的工作方式

BubbleUp 是 Honeycomb 的自動異常歸因功能。操作流程：

1. 在 heatmap 上框選異常區域（例如 latency spike 的時間段跟數值範圍）
2. BubbleUp 把框選區域的 events（outlier set）跟框外 events（baseline set）做統計比較
3. 對每一個 attribute，計算兩組 events 的分布差異（Honeycomb 使用 distribution divergence 量度）
4. 排序差異最大的 attribute 顯示在面板上

BubbleUp 的價值在於它跳過了「猜測哪個維度有問題」的步驟。傳統 metrics dashboarding 需要工程師先想到「可能是某個 region 的問題」→ 加 region filter → 確認。BubbleUp 直接告訴你「outlier set 跟 baseline set 在 region、deployment_version、payment.provider 三個維度上分布最不同」。

BubbleUp 的限制：它需要足夠的 event 量才能做統計比較。低 QPS 服務（< 1 event/sec）在短時間窗內可能沒有足夠的 outlier events。它也不處理因果關係 — 分布差異最大的 attribute 不一定是 root cause，可能是 correlated symptom。

### SLO 與 Burn Rate Alert

Honeycomb 的 SLO 功能把 service-level indicator 定義成一個 query、目標成功率定義成 SLO threshold、窗口跟 burn rate 用來觸發 alert。

SLO 設定要素：

- **SLI query**：定義「成功」的條件。例如 `WHERE duration_ms < 500 AND http.status_code < 500`。
- **SLO target**：例如 99.9%。
- **Window**：通常 30 天 rolling window。
- **Burn rate alert**：multi-window multi-burn-rate。1 小時窗口看快速 burn（14.4x burn rate）、6 小時窗口看中速 burn（6x）、3 天窗口看慢速 burn（1x）。

跟 Prometheus-based SLO 的差異：Prometheus SLO 通常用 recording rule 預先計算 error budget remaining，alert 基於 recording rule 結果。Honeycomb SLO 直接在 event 上做即時計算，不需要 recording rule。代價是 Honeycomb 的 SLO 計算跟平台綁定、不可搬。

對應 [burn-rate](/backend/knowledge-cards/burn-rate/) 概念跟 [4.6 SLI/SLO signal](/backend/04-observability/sli-slo-signal/) 的訊號設計。

## 配置 step-by-step

### Derived Columns

Derived columns 是在 Honeycomb 查詢層建立的計算欄位，不改變原始 event。

常用場景：

- **Duration bucket**：`IF(LTE($duration_ms, 100), "fast", IF(LTE($duration_ms, 500), "normal", "slow"))` — 把連續數值轉成 category、方便 group by
- **Error classification**：`IF(GTE($http.status_code, 500), "server_error", IF(GTE($http.status_code, 400), "client_error", "ok"))` — 對 status code 做語意分類
- **Feature flag analysis**：`CONCAT($service.name, "-", $feature_flag.variant)` — 組合 attribute 做 A/B 比較

Derived columns 的效能影響：它們在查詢時計算，不佔 ingestion 或 storage。但複雜的 derived column expression 會增加查詢 latency。

### Dataset 設計

Honeycomb 的 dataset 是資料隔離的單位。設計決策：

**Option A：per-environment dataset**（production / staging / dev 各自獨立）。優點是查詢預設在單一環境、不需要每次加 environment filter。缺點是跨環境比較需要切換 dataset。

**Option B：per-service dataset**（checkout-api / payment-adapter / notification-service 各自獨立）。優點是單一服務的查詢效能好（資料量小）。缺點是跨服務 trace 需要用 trace view 跨 dataset 查。

**Option C：single dataset per environment**（production 一個大 dataset、所有服務混在一起）。優點是跨服務查詢不需切換、BubbleUp 能跨服務比較。缺點是資料量大、查詢稍慢、不同服務的 attribute 不一致可能造成混淆。

Honeycomb 推薦 Option C — 把同一環境的所有服務放同一個 dataset。理由是 BubbleUp 跟 trace view 的跨服務能力是 Honeycomb 的核心價值，拆太細會削弱這個優勢。用 `service.name` attribute 做 per-service filter。

### OTLP Ingestion

Honeycomb 原生接受 OTLP（gRPC 跟 HTTP）。應用程式用 OTel SDK 產生 traces / logs、設定 OTLP endpoint 為 `api.honeycomb.io:443`、帶 API key header。

```text
# OTel Collector config example
exporters:
  otlp:
    endpoint: "api.honeycomb.io:443"
    headers:
      "x-honeycomb-team": "${HONEYCOMB_API_KEY}"
      "x-honeycomb-dataset": "production"
```

OTel SDK 跟 Honeycomb Beeline SDK 的選擇：新部署一律用 OTel SDK — vendor neutral、可搬。Beeline SDK 是 Honeycomb-specific，已進入維護模式。既有 Beeline 部署可以逐步遷移到 OTel SDK。

## 故障演練與邊界

### Sampling 不足導致成本失控

**觸發條件**：高 QPS 服務（> 10K req/sec）不做 sampling、全量送 Honeycomb。

**表現**：月帳單高於預期。Honeycomb 按 events volume 計費、高 QPS 服務全量 ingestion 的成本可能是 Prometheus 的數倍。

**修復**：部署 Refinery（Honeycomb 的 tail-based sampling proxy）。Refinery 在 trace 完成後決定是否保留 — 保留所有 error trace、保留所有高 latency trace、對正常 trace 做 sampling（例如保留 10%）。Dynamic sampling 根據 traffic pattern 自動調整 sampling rate。

成本與可見度的取捨：1% sampling 意味著 99% 的正常 event 看不到。如果需要回答「過去一小時有多少 successful request」這種 count 問題，sampling 會引入統計誤差。Honeycomb 支援 sample rate annotation — query 結果會用 sample rate 做加權還原。

### BubbleUp 結果不可行動

**觸發條件**：BubbleUp 顯示差異最大的 attribute 是「timestamp」或「trace_id」— 這些 attribute 天然在 outlier set 跟 baseline set 之間分布不同，不提供歸因資訊。

**修復**：在 BubbleUp 設定中排除 high-entropy attribute（trace_id、span_id、timestamp）。Honeycomb 允許設定 BubbleUp 的 ignore list。另外確保 event 帶足夠的 business-context attribute — 如果 event 只有 infra-level attribute（CPU、memory），BubbleUp 能找到的 insight 有限。

### Gaming 高峰的 cardinality 情境

[Gaming 案例](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)揭露了 metrics-first 跟 event-first 系統在高峰期的根本差異。線上遊戲的賽季開跑或限時活動會讓流量在 30 分鐘內暴增 10 倍，同時 per-player、per-match-id 的 label 組合讓 Prometheus 的 active series 從 50 萬爆到 500 萬。

Prometheus 在這個場景的痛點不只是容量 — 而是 cardinality 爆炸改變了系統行為：scrape 變慢導致 metric freshness 從 15 秒退化到數分鐘、recording rule evaluation 跟不上 interval、alert 基於過期數據判斷。修法是 drop per-player label 或做 pre-aggregation、但 drop 掉之後事故時就查不到「哪個玩家的 session 異常」。

Honeycomb 的 event model 在這個場景天然有優勢 — per-player、per-match 是 event 上的 attribute，不產生 series、不影響 ingestion 效能。活動開跑時 event volume 暴增，但 Honeycomb 的 column store 只是行數增加、查詢的 IO 成本線性增長而非指數。BubbleUp 可以在高峰期直接找出「哪些 player_region × match_type 的組合延遲最高」。

代價是成本 — 10 倍的流量意味著 10 倍的 events volume、10 倍的計費。Gaming 場景通常需要搭配動態 sampling：正常 gameplay event 做 1:100 sampling、error 跟 high-latency event 全量保留。Refinery 的 tail-based sampling 在這裡是必備元件。

### Honeycomb vs Prometheus 的共存

Honeycomb 不取代 Prometheus — 兩者解決不同問題。Prometheus 適合已知維度的趨勢監控（error rate dashboard、capacity trending、SLO burn rate），Honeycomb 適合 unknown-unknowns 的事故偵錯。

共存模式：application 用 OTel SDK 同時產生 metrics（→ Prometheus）跟 traces（→ Honeycomb）。Alerting 在 Prometheus 側（因為 metrics aggregation 穩定且成本低），深度偵錯在 Honeycomb 側。

### 雙工具成本治理模式

[觀測成本治理案例](/backend/04-observability/cases/observability-cost-governance-at-scale/)提出一個在中大型團隊反覆驗證的分工：Prometheus 負責 golden signals（低 cardinality、固定 recording rules、成本可預測），Honeycomb 負責 high-cardinality debug（按需查詢、pay per event）。

這個分工的成本結構：Prometheus 的成本隨 active series 數量增長（cardinality-driven）、Honeycomb 的成本隨 event volume 增長（traffic-driven）。兩者的成本 driver 不同、scaling curve 不同 — Prometheus 在 series 爆炸時成本失控、Honeycomb 在 QPS 暴增時成本失控。把兩者放在一起、用各自的成本 sweet spot 互補、比只買一家更能控制總成本。

判讀自己是否需要雙工具的訊號：Prometheus dashboard 已經穩定、但事故時仍需要 20+ 分鐘才能定位到具體 user / request / deployment_version — 這 20 分鐘就是 Honeycomb 的價值。如果事故定位都能在 5 分鐘內靠 Prometheus label 完成，不需要加 Honeycomb。

## 容量與成本

Honeycomb 的計費基於 **events volume**（per million events ingested per month）。Event 的大小（attribute 數量）不直接影響計費（目前模型按 event 筆數、不按 payload size）。

成本治理手段：

- **Sampling**：最直接。10% sampling = 成本降 90%。用 Refinery 做 tail-based sampling 保留重要 trace。
- **Attribute 精簡**：減少不需要的 attribute 不直接降成本（按筆數計費），但能加快查詢。
- **Dataset 合併**：多個小 dataset 合併成一個不影響成本，但能改善 BubbleUp 的統計品質。
- **Team plan vs Enterprise**：不同 plan 的 retention 跟 query 配額不同。

跟 Prometheus 的成本比較：Prometheus 按 time series 數量計（self-host 的話是 infra 成本），Honeycomb 按 event 數量計。高 QPS + 低 cardinality 場景、Prometheus 成本優勢明顯。高 cardinality + 需要深度偵錯場景、Honeycomb 的 event cost 換到的是 BubbleUp 跟 arbitrary group by 的能力。

### 不同規模的成本形態

| 規模                          | 月 event 量     | 預估月成本範圍             | 成本治理重點                                                |
| ----------------------------- | --------------- | -------------------------- | ----------------------------------------------------------- |
| 小型（1-5 服務、< 1K QPS）    | < 50M events    | Free tier 或低帳單         | 不需特別治理                                                |
| 中型（10-30 服務、1-10K QPS） | 50M-500M events | 中等（依 plan）            | Refinery sampling 開始有 ROI                                |
| 大型（50+ 服務、10K+ QPS）    | 1B+ events      | 高（需要 Enterprise plan） | Refinery + 動態 sampling 必備、跟 Prometheus 分工控制總成本 |

大型場景的成本治理核心是 sampling 策略 — 全量 ingestion 的成本通常不可接受。Refinery 的 tail-based sampling 讓 error trace 跟 high-latency trace 全量保留、normal trace 做 1:10 到 1:100 sampling。Sampling rate 的選擇取決於「事故時需要多少正常 trace 做 baseline 比對」— BubbleUp 需要足夠的 baseline events 才能計算分布差異，sampling 太激進會讓 BubbleUp 的統計品質下降。

經驗值：保留至少 5-10% 的正常 trace、同時全量保留所有 error / slow trace。在 Gaming 案例的高峰期，正常 trace 的 sampling 可以暫時降到 1%（高峰流量 10 倍、1% sampling 仍有大量 baseline events），高峰結束後恢復到 10%。動態 sampling 根據當前 QPS 自動調整 — Refinery 的 `DynamicSampler` 會根據 key field（service.name + http.status_code）的分布自動決定 sample rate。

## 整合與下一步

- [Honeycomb 服務頁](/backend/04-observability/vendors/honeycomb/)：overview 與日常操作
- [4.7 cardinality 治理](/backend/04-observability/cardinality-cost-governance/)：cardinality 在 metrics-first 跟 event-first 系統的不同治理策略
- [4.6 SLI/SLO signal](/backend/04-observability/sli-slo-signal/)：SLO / burn rate 的訊號設計
- [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)：OTLP ingestion 的上游標準
- [Prometheus](/backend/04-observability/vendors/prometheus/)：共存模式中的 metrics 面
- [4.C2 Gaming peak cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)：high-cardinality 場景的案例回寫
