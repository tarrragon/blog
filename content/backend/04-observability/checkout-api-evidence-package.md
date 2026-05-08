---
title: "4.22 Checkout API Evidence Package 實作示範"
date: 2026-05-08
description: "用 checkout 路徑示範 evidence package 如何交接給 release gate 與 incident decision。"
weight: 22
tags: ["backend", "observability", "implementation", "evidence-package"]
---

Checkout API evidence package 的核心責任是把同一條交易路徑的訊號整理成可交接證據，讓放行與事故判斷用到同一組事實。

## 服務路徑與邊界

本篇服務路徑是 `client -> checkout-api -> payment-adapter -> order-db`。觀測邊界只處理「這條路徑目前是否可判讀」，不處理重試策略與回退決策本身；後者交給 06 與 08。

要先定義 evidence package 的最小欄位：`Source`、`Time range`、`Query link`、`Owner`、`Data quality`、`Confidence`、`Known gap`。這些欄位在事故期與放行期共用，避免兩套語言。

## 實作步驟

1. 固定交易路徑的觀測主鍵：`trace_id`、`order_id`、`tenant_id`、`region`。
2. 建立三組查詢入口：延遲分布（p50/p95/p99）、錯誤率與錯誤類別、下游 payment dependency timeout。
3. 為每組查詢補欄位：時間窗、資料延遲、採樣比例、目前 owner。
4. 在 deploy 前把同一份 evidence package 連到 [6.8 Release Gate](/backend/06-reliability/release-gate/)。
5. 事故期間把同一份 evidence package 連到 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 判讀訊號

| 訊號                                      | 判讀重點                               | 對應動作                                     |
| ----------------------------------------- | -------------------------------------- | -------------------------------------------- |
| p95 latency 升高但 error rate 無明顯變化  | 可能是下游慢查詢或連線池飽和           | 先查 dependency span 與 DB wait              |
| payment timeout 增加且 trace 斷在 adapter | 下游依賴退化，不是本地 CPU 飽和        | 進 6.8 依賴風險 gate，限制放行               |
| log 有錯誤但 metric 沒反映                | 訊號覆蓋不一致或聚合粒度不對           | 回寫 data quality，補 query 與聚合維度       |
| dashboard 正常但客訴增加                  | 可觀測性盲區或取樣偏差                 | 提升 client-side signal 權重並標示 known gap |
| 同版不同區域行為差異大                    | 區域配置或依賴拓樸差異，非單點程式回歸 | 補 region 維度 evidence，進 8.18 分流 triage |

## 常見誤區

把 evidence package 寫成 dashboard 截圖集合，會失去可重跑性。沒有 query link 與時間窗，事故交班時很難重建判讀脈絡。

把 confidence 省略也會導致誤判。事故前期資料常不完整，若不標示 `suspected` 與 `known gap`，下游決策容易把猜測當成結論。

## 案例回寫

這條路徑可用 [GCP 2019 Network Incident](/backend/08-incident-response/cases/gcp/2019-us-network-congestion-multi-service-incident/) 回寫。先看跨服務訊號如何失真，再回到本章檢查欄位是否能支撐「先分流、再判斷」。

這個案例主要支撐的是「證據欄位完整度」判讀，不直接支撐 release gate 停損門檻設計；停損規則要回到 6.8。

## 跨模組路由

1. 與 4.17 的交接：資料限制與偏差回到 [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。
2. 與 6.8 的交接：放行判斷使用同一份 evidence package。
3. 與 6.23 的交接：驗證證據欄位對齊 [Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)。
4. 與 8.19 的交接：事故決策直接引用 evidence link 與 confidence。

## 下一步路由

要把證據轉成放行條件，接著讀 [6.25 Provider Dependency Release Gate 實作示範](/backend/06-reliability/provider-dependency-release-gate/)。
