---
title: "Locust"
date: 2026-05-15
description: "用 Python user behavior 與 distributed worker 表達高自訂負載模型的效能工程工具"
weight: 4
tags: ["backend", "performance", "capacity", "vendor", "locust", "load-test"]
---

Locust 的核心責任是用 Python 表達高度自訂的使用者行為與 protocol client。它適合 Python 團隊、需要自訂 client、需要 distributed worker、或 scenario 邏輯比工具內建 sampler 更複雜的壓測流程。

## 定位

Locust 適合把壓測寫成一般 Python 程式。當 workload model 需要呼叫 internal SDK、特殊 protocol、複雜資料準備、狀態機、隨機行為或自訂 client，Locust 可以直接使用 Python 生態來表達。

這個定位讓 Locust 接到 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。它能把特殊 client 與下游 dependency 放進同一個 user behavior，但也要求團隊處理 runner、資料與可重現性。

## 適用場景

Python 團隊適合用 Locust 長期維護壓測。既有 domain library、API client、fixture、資料產生器與驗證 helper 都可以被壓測腳本重用。

自訂 protocol 適合用 Locust。HTTP 之外，如果服務需要 gRPC、WebSocket、binary protocol、message broker client 或自家 SDK，Locust 可以直接接 Python library。

Distributed load 適合用 Locust worker 擴展。當單機 Python runner 遇到 CPU 或 connection bottleneck，可以用 master / worker 拆開負載產生能力。

## 選型判準

| 判準                 | Locust 的價值                      | 需要補的能力                           |
| -------------------- | ---------------------------------- | -------------------------------------- |
| Python user behavior | 複雜使用者邏輯容易表達             | 腳本工程紀律與可重現性                 |
| Custom client        | 可直接使用 Python protocol library | client latency 與 runner overhead 校正 |
| Distributed worker   | master / worker 便於擴負載         | worker sizing、網路與結果聚合          |
| Web UI / headless    | 探索與 CI 都能支援                 | 長期 artifact 與 threshold 語意        |

Python user behavior 價值來自表達能力。當使用者行為包含條件分支、資料依賴、狀態轉移與 domain helper，Locust 能把壓測寫成接近業務流程的程式。

Custom client 價值來自 protocol 彈性。工具內建 protocol 覆蓋不足時，Locust 可以改用 Python library；代價是 runner overhead 與 client behavior 也要被納入證據品質。

## 跟其他工具的取捨

Locust 和 k6 的主要差異是彈性與 runner 效率。Locust 用 Python 取得自訂能力；k6 用 Go runtime 與 JavaScript-style scripting 提供較輕的 runner 與 CI workflow。

Locust 和 JMeter 的主要差異是協作模式。Locust 偏工程團隊、Python code review 與 custom client；JMeter 偏 GUI、plugin 與非工程角色協作。

Locust 和 Gatling 的主要差異是語言生態。Locust 適合 Python 與 domain library；Gatling 適合 JVM simulation、injection profile 與 report。

Locust 和 Vegeta 的主要差異是行為複雜度。Vegeta 適合簡單 HTTP probe；Locust 適合多步驟 user behavior 與 custom protocol。

## 操作成本

Locust 的主要成本是 runner overhead 與分散式治理。Python runner 的效能上限要用 worker scale-out 解決；壓測結論要同時檢查目標服務 saturation 與 worker 本身 CPU、connection、network 是否已成瓶頸。

腳本工程成本來自自由度。Python 可以很快寫出複雜行為，也容易把測試資料、randomness、side effect、sleep 與 exception handling 寫散；團隊要維持 scenario structure、fixture、logging 與 artifact 標準。

自訂 client 成本來自校正。使用 SDK 或 custom protocol client 時，要確認 client retry、timeout、connection pool 與 serialization 行為是否接近 production，避免 runner 模擬出不存在的壓力形狀。

## Evidence Package

Locust 結果應回寫到 evidence package。最小欄位包括 locustfile version、user class、task weight、spawn rate、worker count、client library version、target environment、p95 / p99、error rate、throughput、target saturation metric、known gap 與 owner。

| 欄位         | Locust 證據來源                                 |
| ------------ | ----------------------------------------------- |
| Source       | locustfile、CSV / JSON result、dashboard link   |
| Time range   | test start / end                                |
| Query link   | APM / metrics / logs 查詢連結                   |
| Data quality | user behavior coverage、fixture freshness       |
| Confidence   | worker capacity、client realism                 |
| Known gap    | worker bottleneck、custom client 偏差、資料偏差 |

Evidence package 的核心用途是區分目標瓶頸與 runner 瓶頸。Locust 分散式測試要同時保存 worker 數量、worker 資源、spawn rate 與 client behavior，讓 reviewer 知道壓力是否真的打到目標服務。

## 案例回寫

Locust 適合回寫需要高度自訂 user behavior 的案例。它可接 [9.C28 FanDuel 雙峰 workload](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的投注行為模型、[9.C16 SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 admission / token flow、[9.C26 PayPay mobile payment messaging](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) 的外部推送與下游 quota 模擬、[9.C8 Niantic Pokémon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) 的玩家移動 + 互動混合行為，以及 [9.C18 Zoom COVID 30x surge](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 的會議建立 / 加入 / 離開行為混合。

這些案例的重點是 domain behavior。Locust 頁引用案例時，要把 case 轉成 user class、task weight、custom client、downstream mock 與 worker capacity，再把總 RPS 放回這些行為條件下判讀 — 例如 Pokémon GO 玩家行為跟一般 web user 完全不同（持續 GPS 上報 + 偶發互動），不能直接用 HTTP RPS 衡量。

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 平行：[k6](/backend/09-performance-capacity/vendors/k6/)、[JMeter](/backend/09-performance-capacity/vendors/jmeter/)、[Gatling](/backend/09-performance-capacity/vendors/gatling/)
- 官方：[Locust documentation](https://docs.locust.io/)
