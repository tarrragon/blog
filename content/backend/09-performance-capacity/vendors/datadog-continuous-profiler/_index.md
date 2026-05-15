---
title: "Datadog Continuous Profiler"
date: 2026-05-15
description: "用 SaaS APM 整合、deployment marker 與 profile diff 支援 release regression 定位的 profiling 工具"
weight: 30
tags: ["backend", "performance", "capacity", "vendor", "datadog", "profiling"]
---

Datadog Continuous Profiler 的核心責任是把 production profile 接到 SaaS APM、deployment marker、service tag 與 release regression workflow。它適合已經使用 Datadog APM / metrics / logs 的團隊，重點在讓 slow request、resource saturation、deploy version 與 profile diff 能在同一個操作介面中對齊。

## 定位

Datadog Continuous Profiler 適合 all-in-one observability 團隊。當服務已經用 Datadog agent、APM trace、runtime metrics 與 deployment tracking，profiler 可以把 CPU、allocation、wall time、lock 與 runtime profile 加進同一個服務視角。

這個定位讓 Datadog Continuous Profiler 接到 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 與 [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)。它的價值在於降低 profile diff 的交接成本；它的代價在於 SaaS 成本、agent 設定、資料保留與 vendor 約束。

## 適用場景

Release regression 定位適合 Datadog Continuous Profiler。當 canary 或 release candidate 的 p99、CPU、memory 或 cost per request 退化，團隊可以用 deployment marker 對比 release 前後 profile，找出變寬的 call stack。

APM-to-profile drilldown 適合 Datadog Continuous Profiler。慢 request 可以從 service、endpoint、trace 或 span 往下切到 profile，讓工程師知道 latency 是 DB、network、runtime、serialization、lock 還是 CPU hot path。

多語言 SaaS 團隊適合 Datadog Continuous Profiler。團隊如果同時維護 Go、Java、Python、Ruby、Node.js 或 .NET 服務，SaaS profiler 可以用統一 tag、dashboard 與權限模型管理。

## 選型判準

| 判準              | Datadog 的價值                           | 需要補的能力                     |
| ----------------- | ---------------------------------------- | -------------------------------- |
| APM 整合          | trace、service、endpoint、profile 可串接 | service tag 與 deploy label 紀律 |
| Deployment marker | release 前後 profile diff 容易建立       | release pipeline 與版本標記整合  |
| SaaS 操作         | 低自管成本、跨團隊易查詢                 | 成本治理、資料保留與 vendor 約束 |
| 多語言支援        | 多 runtime 用同一套操作介面              | 各語言 agent overhead 與覆蓋差異 |

APM 整合價值來自上下文連續。Metrics 告訴你 CPU 上升，trace 告訴你 endpoint 變慢，profile 告訴你哪段 code path 變貴；Datadog 的優勢是把這些訊號放進同一個查詢與 dashboard 流程。

Deployment marker 價值來自 release gate。Profile diff 如果能對齊 commit、version、environment 與 canary cohort，就能成為 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/) 的 evidence。

## 跟其他工具的取捨

Datadog Continuous Profiler 和 Pyroscope 的主要差異是操作模型。Datadog 偏 SaaS all-in-one 與 APM 整合；Pyroscope 偏 Grafana / OSS 生態與可自管。

Datadog Continuous Profiler 和 Parca 的主要差異是 profiling 方法與平台責任。Datadog 偏 agent + SaaS product workflow；Parca 偏 eBPF / always-on profiling 與開源平台治理。

Datadog Continuous Profiler 和一次性 runtime profiler 的主要差異是時間維度。一次性 profiler 適合本機或 incident 當下調查；continuous profiler 適合 baseline、release diff 與長期退化治理。

## 操作成本

Datadog Continuous Profiler 的主要成本是資料量與保留。Profile sample、tag cardinality、service 數量、environment 數量與 retention 都會影響費用與查詢體驗。

Agent 成本來自 runtime 差異。不同語言的 profiler 支援、overhead、可觀測維度與限制不同，導入時要用 canary service 量測 CPU、memory、latency 與 profile completeness。

Vendor 成本來自資料與 workflow 綁定。當 profile diff、release marker、APM drilldown 與 incident workflow 都在 Datadog 中，後續切換平台需要重新建立 tag schema、dashboard、retention 與 gate integration。

## Evidence Package

Datadog Continuous Profiler 結果應回寫到 evidence package。最小欄位包括 service、version、environment、deploy marker、profile type、time range、comparison baseline、profile diff link、overhead estimate、known gap 與 owner。

| 欄位         | Datadog 證據來源                             |
| ------------ | -------------------------------------------- |
| Source       | profiler view、profile diff、APM link        |
| Time range   | baseline / candidate profile window          |
| Query link   | Datadog profile、trace、dashboard link       |
| Data quality | service tag、version tag、sampling status    |
| Confidence   | production coverage、agent overhead          |
| Known gap    | runtime coverage、tag drift、retention limit |

Evidence package 的核心用途是讓 release regression 可追溯。Reviewer 要能從 failed gate 直接打開 profile diff，看出哪個 service、version、endpoint 或 call stack 造成資源成本變化。

## 案例回寫

Datadog Continuous Profiler 適合回寫 release regression 與 APM 整合案例。它可接 [Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 profile noise 降低、[Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的 low-latency hot path 定位，以及 [Datadog OTel migration practice](/backend/04-observability/cases/datadog-otel-migration-practice/) 的 observability pipeline 整合。

這些案例的重點是上下文對齊。Datadog Profiler 頁引用案例時，要把 case 轉成 service tag、deploy marker、profile diff、trace drilldown 與 release gate evidence。

## 下一步路由

- 上游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 上游：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)
- 跨模組：[4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 平行：[Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/)
- 平行：[Parca](/backend/09-performance-capacity/vendors/parca/)
- 官方：[Datadog Continuous Profiler documentation](https://docs.datadoghq.com/profiler/)
