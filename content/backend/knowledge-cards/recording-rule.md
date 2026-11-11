---
title: "Recording Rule"
date: 2026-06-22
description: "說明把 query-time 聚合計算推到寫入時的 pre-aggregation 機制"
weight: 325
tags: ["backend", "observability"]
---

Recording rule 把重複的聚合計算從查詢時推到寫入時。當 dashboard 或 alert 反覆對同一組 raw [metrics](/backend/knowledge-cards/metrics/) 做 rate / sum / histogram_quantile，每次查詢都重新掃描原始資料；recording rule 把計算結果預先寫成新的 time series，查詢時直接讀取結果。

## 跟其他概念的關係

Recording rule 是 [metrics](/backend/knowledge-cards/metrics/) 讀取路徑的效能工具。它在 TSDB 層（如 Prometheus、Thanos、Mimir）定期執行 query expression，把結果作為新 series 寫入儲存。概念上類似 OLAP 的 [materialized view](/backend/knowledge-cards/materialized-view/)，但作用在時間序列而非關聯式資料。

## 判斷條件與後果

Recording rule 的名稱與維護責任，決定讀取端能不能判斷自己讀到的是什麼。名稱照 `level:metric:operations` 的慣例（如 `job:http_requests_total:rate5m`）時，讀者從名稱判斷得出來源、粒度與計算方式；名稱不照慣例時，要回頭查規則定義。沒有指定維護責任時，計算表達式引用的原始指標改名或消失之後，規則產生空結果，依賴它的 dashboard 與 alert 跟著失效，而沒有人負責修正規則。

Recording rule 產生的 series 本身也佔儲存空間與 [cardinality](/backend/knowledge-cards/metric-cardinality/)。規則數量增長時，一輪規則的 evaluation duration 逐漸接近執行間隔；一輪在下一輪開始前跑不完時，rule group lag 上升，dashboard 讀到的是過期的預計算結果。所以 rule evaluation duration 與 rule group lag 列入監控。

## 使用情境

需要 recording rule 的訊號是 dashboard panel 載入時間持續退化、或 alert rule 因為 query timeout 而漏發。把 SLO burn rate 計算、高流量 endpoint 的 rate 與 error ratio 預先聚合成 recording rule，是最常見的起點。

Recording rule 與 raw query 的分工：高頻讀取（dashboard 自動刷新、alert 每分鐘 evaluate）適合 recording rule；低頻即席查詢（事故時的 ad-hoc 切片）直接查 raw series，保留完整維度。

在觀測領域的應用見 [4.2 metrics 聚合查詢](/backend/04-observability/metrics-basics/) 跟 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。
