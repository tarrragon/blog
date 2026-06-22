---
title: "4.2 metrics 與 SLI/SLO"
date: 2026-04-23
description: "整理 counter、gauge、histogram 與服務健康指標"
weight: 2
tags: ["backend", "observability"]
---

## 大綱

- [metrics](/backend/knowledge-cards/metrics/) 基本型別
- latency [histogram](/backend/knowledge-cards/histogram/)
- error rate / [throughput](/backend/knowledge-cards/throughput/)
- [SLI / SLO](/backend/knowledge-cards/sli-slo/) / [error budget](/backend/knowledge-cards/error-budget/)

## 概念定位

[metrics](/backend/knowledge-cards/metrics/) 是把服務狀態壓縮成可聚合、可比較、可告警的時間序列，責任是讓團隊看見趨勢、容量與服務健康。

這一頁處理的是 metric 型別與計算語意。counter、gauge 與 [histogram](/backend/knowledge-cards/histogram/) 各自回答不同問題；選錯型別會讓後面的 SLI、dashboard 與 alert 都建立在錯誤訊號上。

## 核心判讀

判讀 metrics 時，先看指標型別是否對應問題，再看分母、bucket 與 label 是否穩定。

重點訊號包括：

- latency 是否用 [percentile](/backend/knowledge-cards/percentile/) / [histogram](/backend/knowledge-cards/histogram/) 補足 average 的盲點
- error rate 的分母是否能代表真實請求量
- bucket 是否覆蓋實際尾端延遲
- label 是否能切出必要維度，同時不讓 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) 失控

## 判讀訊號

- 用 average 而非 percentile 追 latency、p99 失真
- counter / gauge 混用、計算公式錯
- histogram bucket 沒對齊實際分佈、tail latency 被截斷
- error rate 分母不穩（流量低時誤觸發、高時稀釋）
- 商業 SLI 跟 metric 對不上、靠人解釋

## 聚合查詢與 recording rule

Metrics 的讀取面跟寫入面是兩個不同的效能瓶頸。寫入面的壓力來自 series 數量（[cardinality](/backend/knowledge-cards/metric-cardinality/)）；讀取面的壓力來自查詢時的聚合計算量。兩者可以獨立失控 — series 數量合理但每次 dashboard 刷新都重算複雜表達式，query engine 一樣會過載。

### Query-time aggregation 的成本

Dashboard panel 或 alert rule 每次觸發時，TSDB 對 raw series 執行聚合表達式（rate、sum、histogram_quantile）。當 raw series 數量大、查詢時間範圍長、dashboard 刷新頻率高，同一個計算會被反覆執行。

一個典型的 SLO [burn rate](/backend/knowledge-cards/burn-rate/) panel 可能涉及：先算 rate、再除以 total、再跟 threshold 比較、最後乘以 window。每次刷新把整條運算鏈走一遍。當這類 panel 有十幾個、每 30 秒刷新一次，query engine 的 CPU 會被 dashboard 佔滿，留給事故即席查詢的餘量不夠。

### Recording rule 把計算推到寫入時

[Recording rule](/backend/knowledge-cards/recording-rule/) 是 Prometheus 生態（包括 Thanos、Mimir、VictoriaMetrics）的標準應對方式：在 TSDB 內定期執行聚合表達式，把結果寫成新的 time series。Dashboard 跟 alert rule 讀 recording rule 的輸出而非重算 raw series。

Recording rule 的設計判準是查詢頻率跟計算成本的乘積。高頻讀取（dashboard auto-refresh、每分鐘 evaluate 的 alert rule）加上高計算成本（多維度 rate + ratio + quantile）的組合最值得做 recording rule。低頻即席查詢（事故時的 ad-hoc 切片）直接查 raw series，保留完整維度。

Recording rule 的命名慣例用 `level:metric:operations` 格式（如 `job:http_requests_total:rate5m`），讓讀者從名稱直接判斷來源粒度跟計算方式。沒有命名慣例時，recording rule 增長到數百條後會難以維護跟除錯。

### Rollup 與 downsampling

[Rollup](/backend/knowledge-cards/rollup/) 解決的是時間維度的讀取成本。原始資料以 15 秒間隔採集，查詢「過去 90 天的 error rate 趨勢」時需要掃描數百萬個資料點；rollup 把舊資料聚合成 5 分鐘或 1 小時粒度，查詢時只讀取聚合後的少量資料點。

Rollup 的聚合函數選擇影響查詢語意。Counter 用 sum 合理、gauge 用 average 合理、histogram 用 average 會失去分布資訊（p99 被壓平）。設計 rollup 時要按 metric type 指定對應的聚合函數，混用會讓長時間範圍的 dashboard 產生誤導性數值。

查詢路由的透明度也是設計重點。使用者把 dashboard 時間範圍從 1 小時拉到 7 天時，系統自動從 raw series 切到 rollup series，精度從 15 秒變成 5 分鐘。如果這個切換對使用者不透明，事故中觀察到的數值變化可能是精度切換的假象而非真實服務變化。

### Metrics 讀取面的資源隔離

Metrics 的 query engine 跟 log 一樣面臨多種查詢模式競爭資源的問題。Dashboard 定期刷新是穩定的背景負載；alert rule evaluation 是系統關鍵的定期負載；事故即席查詢是偶發的突增負載。三者搶同一個 query engine 時，dashboard 跟 alert 的穩定負載會壓縮即席查詢的可用資源。

Prometheus 原生的資源隔離有限，但 Thanos Query Frontend、Mimir Query Frontend、Grafana Cloud 的 query scheduler 都支援 query priority 或 query queue 分離。設計時把 alert evaluation 設為最高優先（告警不能因 query 排隊而延遲），dashboard 次之，即席查詢的延遲容忍最高但不能被完全餓死。

## 交接路由

- 04.6 SLI/SLO 訊號設計：把 metric 升級為 user-journey SLI
- 04.7 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) / cost：label 治理與成本邊界
- 04.9 continuous profiling：metrics 之外的第四角觀測訊號
- 04.23 [觀測查詢設計](/backend/04-observability/observability-query-design/)：跨訊號類型的讀取路徑系統設計
- [4.C11 Uber M3](/backend/04-observability/cases/uber-m3-metrics-platform-scale/)：單機 Prometheus 到平台級 metrics 系統的演進
