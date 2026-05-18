---
title: "Vegeta"
date: 2026-05-15
description: "用簡潔 CLI 與固定 rate HTTP attack 快速探測 latency、throughput 與 saturation 的效能工程工具"
weight: 5
tags: ["backend", "performance", "capacity", "vendor", "vegeta", "load-test"]
---

Vegeta 的核心責任是用簡潔 CLI 對 HTTP endpoint 產生固定 rate 負載，快速探測 latency、throughput、error rate 與 saturation。它適合單一 endpoint、少量 header / body 變化、快速 baseline、incident 後驗證與工程師本機或 CI 中的輕量壓測。

## 定位

Vegeta 適合快速回答「這個 endpoint 在某個 rate 下表現如何」。當團隊需要先找出大概 knee point、驗證一個修補是否降低 latency、或在 CI 裡跑小型 performance smoke test，Vegeta 的 CLI workflow 很直接。

這個定位讓 Vegeta 接到 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。它提供的是快速壓力探針，後續若要表達複雜 workload model，通常要轉向 k6、Gatling、Locust 或 JMeter。

## 適用場景

單 endpoint saturation probe 是 Vegeta 的主要入口。工程師可以對 login、search、read API、feature flag endpoint 或 internal health-like endpoint 施加固定 rate，觀察 p95 / p99 與 error rate 何時開始上升。

Regression smoke test 適合用 Vegeta。CI 或 pre-release 可以用短時間固定 rate 測試，確認 hot path 沒有明顯退化，再把更完整的 scenario 交給 k6、Gatling 或 Locust。

Incident 後修補驗證適合用 Vegeta。當事故根因是某個 endpoint 的 query、cache miss、lock contention 或 timeout，修補後可以用相同 request set 重跑，快速比較 latency distribution。

## 選型判準

| 判準       | Vegeta 的價值                   | 需要補的能力                        |
| ---------- | ------------------------------- | ----------------------------------- |
| CLI 簡潔   | 本機、CI、shell workflow 容易接 | 長期報表與 artifact 標準化          |
| 固定 rate  | 探測 rate / latency 關係清楚    | 複雜使用者行為與 arrival pattern    |
| HTTP 導向  | API hot path 快速驗證           | 非 HTTP protocol 與 multi-step flow |
| 快速 probe | 適合 smoke test 與修補驗證      | 完整 workload model 與資料治理      |

CLI 簡潔價值來自低摩擦。當問題還在定位階段，工程師可以很快產生可重跑 command 與 target file，先取得 baseline，再決定是否需要完整壓測平台。

固定 rate 價值來自可比較。用相同 request set、rate、duration 與 target environment 重跑，可以讓修補前後的 latency distribution 有清楚對照。

## 跟其他工具的取捨

Vegeta 和 k6 的主要差異是 scenario 深度。Vegeta 適合固定 rate HTTP probe；k6 適合多步驟 scenario、threshold、CI artifact 與 browser-style flow。

Vegeta 和 JMeter 的主要差異是工具重量。Vegeta 適合快速 CLI；JMeter 適合 GUI、多 protocol、plugin 與企業測試資產。

Vegeta 和 Gatling 的主要差異是長期維護模式。Vegeta 用 command / target file 保持簡單；Gatling 用 simulation 維護複雜 flow 與 injection profile。

Vegeta 和 Locust 的主要差異是自訂能力。Locust 適合 Python user behavior 與 custom client；Vegeta 適合 HTTP endpoint 的直接壓力測量。

## 操作成本

Vegeta 的主要成本是 workload coverage 有限。它能快速測 endpoint，但多步驟 session、資料依賴、payment mock、queue side effect 與 realistic user journey 需要額外工具或腳本補上。

Artifact 成本來自命令可追溯性。每次測試要保存 rate、duration、targets、headers、body、環境、版本與結果檔；否則快速 probe 很容易變成不可比較的一次性觀察。

Runner 成本通常較低，但仍要檢查本機瓶頸。高 rate 測試時，產生負載的機器也可能先被 CPU、network、file descriptor 或 connection limit 卡住。

## Evidence Package

Vegeta 結果應回寫到 evidence package。最小欄位包括 command、target file hash、rate、duration、workers、target environment、p95 / p99、max latency、error rate、throughput、target saturation metric、known gap 與 owner。

| 欄位         | Vegeta 證據來源                                 |
| ------------ | ----------------------------------------------- |
| Source       | command、targets file、binary result、report    |
| Time range   | test start / end                                |
| Query link   | APM / metrics / logs 查詢連結                   |
| Data quality | target set freshness、header / body correctness |
| Confidence   | runner capacity、endpoint representativeness    |
| Known gap    | 未覆蓋多步驟 flow、資料偏差、runner limit       |

Evidence package 的核心用途是讓快速測試可以比較。Vegeta 的結果通常很短，反而更需要保存 command 與 target set，讓下一次修補驗證能跑同一組條件。

## 案例回寫

Vegeta 適合回寫單 endpoint hot path 與修補驗證案例。它可接 [9.C3 Coinbase ultra-low latency](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 的 sub-millisecond latency distribution 判讀、[9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的 p99 < 10ms lookup 驗證、[9.C29 Lemino connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 的 RDB bottleneck 探測、[9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) 的次毫秒 cache lookup 驗證，以及 [9.C5 Amazon Ads DynamoDB](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的 hot partition 探測。

這些案例的重點是快速定位與比較。Vegeta 頁引用案例時，要把 case 轉成 endpoint、rate、duration、latency budget、target saturation metric 與 runner limit — 例如 Coinbase 的 sub-ms 目標要求 Vegeta runner 必須跟 target 同 placement group、否則 runner 自身的網路 jitter 會吃掉觀測精度。

## 下一步路由

- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 平行：[k6](/backend/09-performance-capacity/vendors/k6/)、[Gatling](/backend/09-performance-capacity/vendors/gatling/)、[Locust](/backend/09-performance-capacity/vendors/locust/)
- 跨模組：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 官方：[Vegeta documentation](https://github.com/tsenart/vegeta)
