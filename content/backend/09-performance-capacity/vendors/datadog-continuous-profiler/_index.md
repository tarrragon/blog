---
title: "Datadog Continuous Profiler"
date: 2026-05-15
description: "用 SaaS APM 整合、deployment marker 與 profile diff 支援 release regression 定位的 profiling 工具"
weight: 30
tags: ["backend", "performance", "capacity", "vendor", "datadog", "profiling"]
---

Datadog Continuous Profiler 的核心責任是把 production profile 接到 SaaS APM、deployment marker、service tag 與 release regression workflow。它適合已經使用 Datadog APM / metrics / logs 的團隊，重點在讓 slow request、resource saturation、deploy version 與 profile diff 能在同一個操作介面中對齊。

## 定位

Datadog Continuous Profiler 是 [Datadog](/backend/04-observability/vendors/datadog/) APM 的 *production profiling* add-on、跟 Datadog Logs / Metrics / Traces 同 plane、共用 service tag、env tag、version tag 與 query bar。它的核心責任是把 production profile 接到 SaaS APM、deployment marker、service tag 與 release regression workflow，讓 slow request、resource saturation、deploy version 與 profile diff 能在同一個操作介面中對齊。

跟 [Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/) / [Parca](/backend/09-performance-capacity/vendors/parca/) 這類 OSS profiler 比、Datadog Continuous Profiler 走 *ecosystem-bundled* 路線 — profiler 本身不獨立計費、跟 APM host 一起進 business unit 預算、profile data 直接跟 trace_id、deploy marker、log query 在同一介面 cross-link。OSS profiler 走 *standalone deployment*、profile store 自管（ClickHouse / object storage）、跟 observability 其他 plane 要自己 wire（grafana correlation、自寫 trace_id mapping）。差異不在 *flame graph 本身的視覺呈現*、而在 *跨 signal 的 query continuity 跟組織計費歸屬*。

這個定位讓 Datadog Continuous Profiler 接到 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 與 [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)。它的價值在於降低 profile diff 的交接成本；它的代價在於 SaaS 成本、agent 設定、資料保留與 vendor 約束。

## 最短判讀路徑

判斷 Datadog Continuous Profiler deployment 是否健康、最少看四件事：

- **Agent / SDK profiling 是否真的 enabled**：Datadog Agent 跑著不等於 profiler 開了 — 各語言要在 SDK init 加 `profiling_enabled=true` 或環境變數 `DD_PROFILING_ENABLED=true`、Go / Java / Python / Node / Ruby / .NET 的開啟方式跟覆蓋的 profile type（CPU / heap / goroutine / lock / wall time）各不同
- **Service / version / env tag 紀律**：profile 沒有 `service` + `env` + `version` tag 就無法 diff、release marker 也對不上 — CI 要把 git SHA 或 release tag 注入 `DD_VERSION`、deploy pipeline 要打 deployment marker API
- **Sampling rate 跟 production coverage**：profiler 預設 60s 採一次、低流量服務或 short-lived 任務可能 sample 不到 hot path — 對 ultra-low latency / burst workload 要評估 sampling 是否還抓得到 regression signal
- **Profile ingestion cost / retention**：profile 是按 APM host 計費、但 profile event 量隨 service 數量 + sampling rate 漲、retention 預設 7 天（custom retention 另計）— 大型 deployment 要做 service-level enable/disable governance

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

## 核心取捨表

| 取捨維度          | Datadog Continuous Profiler                            | Pyroscope                                         | Parca                                   |
| ----------------- | ------------------------------------------------------ | ------------------------------------------------- | --------------------------------------- |
| 部署模型          | SaaS only、跟 Datadog Agent / APM 綁                   | OSS self-host / Grafana Cloud SaaS                | OSS self-host（Polar Signals SaaS 選）  |
| 計費模型          | 跟 APM host 計費（profile 不獨立 metering）            | OSS 免費 / Grafana Cloud 按 ingestion             | OSS 免費 / SaaS 按 host                 |
| Profile 採集方式  | Language SDK（pull 採樣）                              | SDK + eBPF agent                                  | eBPF-first、language-agnostic           |
| Trace correlation | 強 — trace_id 自動 link 到 flame graph                 | 中 — 要自己 wire OTel trace_id                    | 弱 — 偏 eBPF profile、trace 整合較淺    |
| 視覺 / Workflow   | APM service view + Profile diff + Code Hotspot in IDE  | Grafana flame graph + diff、跟 Loki / Tempo 同 UI | Parca UI 簡潔、偏單純 profile 探索      |
| 多語言支援        | Go / Java / Python / Node / Ruby / .NET / PHP 官方 SDK | 同 + 社群 SDK；eBPF 補 native binary              | eBPF-only、不挑語言但 symbol 解析較吃力 |
| Vendor lock-in    | 高 — profile 跟 APM workflow 綁、退場要重建 dashboard  | 低 — OSS、profile 格式相對開放                    | 低 — OSS、pprof 格式相容                |
| 適合場景          | Datadog-heavy org、APM / log / metric 已用             | Grafana stack 已用、要省 license                  | eBPF-first、low-overhead always-on      |

選 Datadog Continuous Profiler 的核心訴求：*Datadog 已是 observability backbone* + 要 *APM trace ↔ profile drilldown 是 first-class workflow* + 接受 SaaS 計費 + 接受 SDK overhead trade-off。如果 Datadog 不是既有平台、單純為了 profiling 引入 Datadog 通常成本不划算、改走 Pyroscope / Parca。

跟一次性 runtime profiler（`pprof`、`async-profiler` 手動跑）的差異是時間維度。一次性 profiler 適合本機或 incident 當下調查；continuous profiler 適合 baseline、release diff 與長期退化治理 — 兩者互補、不互斥。

## 進階主題

**APM trace ↔ profile correlation**：Datadog SDK 把 `trace_id` 注入 profile sample 的 label、APM trace view 上每個 span 可以直接點到「執行這段 span 時的 flame graph」。意義是 *p99 latency 異常 trace 不只看 span 等待時間、能直接看到該 span 期間 CPU / lock / allocation 真正花在哪段 code*。需要 SDK 版本支援 + trace context propagation 正確接上、舊版 SDK 或自寫 instrumentation 容易斷鏈。

**Endpoint profiling**：profile 按 HTTP endpoint / RPC method 切片、不只看 service 整體 hot path。意義是 *新加的 endpoint 即便 traffic 小、也能單獨看它的 CPU / allocation cost*、不會被 service 主流量稀釋。對 multi-tenant API、A/B test endpoint、internal admin endpoint 的退化偵測特別有用。

**Code Hotspot in IDE**：Datadog IDE plugin（IntelliJ / VS Code）把 production profile 的 hot line 直接 overlay 到 source code、工程師 review PR 時能看到「這個 function 在 production 佔 service CPU 12%」。降低 *看 flame graph → 找 source 對應行* 的 cognitive cost。對應 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 中「production signal → code change」的 feedback loop 縮短。

**Profile diff（baseline vs candidate）**：Datadog 內建 diff view、選兩個 time window 或兩個 version tag、直接看 flame graph 哪些 frame 變寬 / 變窄。是 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/) 的核心 evidence — canary 跑完 30min、自動拉 baseline vs candidate diff 報告、超過 threshold 阻擋 promote。

**Notebooks correlation**：Datadog Notebooks 可以把 profile flame graph、APM trace、metric chart、log query 排在同一份文件。incident post-mortem 跟 release review 寫一份 notebook 比散落多個 dashboard tab 更可追溯、也接 [evidence package](/backend/04-observability/observability-evidence-package/) 規範。

## 排錯與失敗快速判讀

- **SDK overhead 在 production 過高**：profiler 預設 overhead < 2% CPU、但 wall-time profiling / allocation profiling 全開可能到 5%+ — canary 一台量測、按 profile type 分別 enable、不要全部一次開
- **Sampling rate 太低 / false negative**：short-lived job（< 60s）或 low-traffic service 可能整個生命週期沒被 sample 到、看不到 hot path — 改成事件觸發 profile（on-demand profiling API）或拉高該 service 的 sampling rate
- **Profile 沒有 version tag / 無法 diff**：deploy pipeline 沒注入 `DD_VERSION`、release marker 對不上 — 補 CI 環境變數、用 `dd-trace` SDK 自動讀 git commit SHA、跑 staging 驗證 diff view 能顯示 version
- **Trace ↔ profile drilldown 斷鏈**：SDK 版本太舊、或 trace context 在非同步 / queue handler 沒 propagate — 升 SDK + 補 trace context propagation、用一條已知慢 trace 驗證能不能跳到 flame graph
- **Profiling cost spike**：新 service 開啟 profiling、或某 service profile event 暴增（exception 路徑反覆採樣）— 看 Datadog usage dashboard 的 profile host hour、對嫌疑 service 暫關 profiling 觀察 cost 曲線、再 tune sampling rate
- **Flame graph symbol 解析失敗 / 顯示 `?` frame**：缺 debug symbol、stripped binary、或語言 runtime 版本不支援 — 補 build 時保留 symbol、確認 SDK 版本 vs runtime 版本對應表
- **Lock profile 看不出 contention**：某些語言（Go / Java）的 lock profiling 需要額外 flag（`DD_PROFILING_BLOCK_ENABLED` / `DD_PROFILING_LOCK_ENABLED`）— 預設沒開、要明確 enable 才看得到 lock contention flame graph

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

Datadog Continuous Profiler 適合回寫 release regression 與 APM 整合案例。它可接 [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 profile noise 降低、[9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的 low-latency hot path 定位、[9.C3 Coinbase ultra-low latency exchange](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 的 z1d 單執行緒 hot path 分析、[9.C7 Lyft 100+ 微服務](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/) 的 per-service profile diff，以及 [Datadog OTel migration practice](/backend/04-observability/cases/datadog-otel-migration-practice/) 的 observability pipeline 整合。

這些案例的重點是上下文對齊。Datadog Profiler 頁引用案例時，要把 case 轉成 service tag、deploy marker、profile diff、trace drilldown 與 release gate evidence — 例如 Coinbase sub-ms 目標下、profile 必須對齊 RAFT consensus 跟 placement group 拓樸、才能解釋 hot path 為何在某些 epoch 才出現。

## 下一步路由

- 上游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 上游：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)
- 跨模組：[4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 平行：[Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/)
- 平行：[Parca](/backend/09-performance-capacity/vendors/parca/)
- 官方：[Datadog Continuous Profiler documentation](https://docs.datadoghq.com/profiler/)
