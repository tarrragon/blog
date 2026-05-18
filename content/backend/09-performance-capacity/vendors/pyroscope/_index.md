---
title: "Pyroscope"
date: 2026-05-15
description: "用 Grafana 生態與開源 profiling backend 建立可自管 profile diff 與 flame graph 的工具"
weight: 31
tags: ["backend", "performance", "capacity", "vendor", "pyroscope", "profiling"]
---

Pyroscope 的核心責任是提供開源 continuous profiling backend，讓團隊用 Grafana 生態保存、查詢、比較與視覺化 production profile。它適合偏 OSS-first、已使用 Grafana / Prometheus / Tempo / Loki 的團隊，重點在把 CPU、memory、allocation 與 profile diff 放進可自管 observability stack。Pyroscope 原為獨立 OSS 專案、*2023 年被 Grafana Labs 收購*、現分兩條產品線：*Grafana Pyroscope*（OSS、Apache 2.0、self-host）與 *Grafana Cloud Profiles*（商業 SaaS、走 Grafana Cloud 計費）。

## 服務定位

Pyroscope 在 continuous profiling 賽道上的差異點是 *Grafana Labs 整合 + 多語言 SDK 覆蓋*、而不是 profiling 演算法本身。跟 [Parca](/backend/09-performance-capacity/vendors/parca/) 比、Parca 走 *pprof + Prometheus-style label* 的 CNCF / eBPF infrastructure profiling 路線、focus 在 system-wide 一次抓全機；Pyroscope 走 *per-language SDK + Grafana stack 整合* 的 developer-facing 路線、focus 在 application-level flame graph 與 release diff。跟 [Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/) 比、Datadog 走 *SaaS all-in-one + APM 同 trace context*、profiling 自動跟 trace span 關聯；Pyroscope 走 *self-host 可選 + Grafana 跨 signal*、整合靠 Grafana dashboard 跟 explore link 而非 product-level deep linking。

這個定位讓 Pyroscope 接到 [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/) 與 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)。它的價值在於 OSS / Grafana 整合與可自管；它的代價在於 storage、retention、agent rollout 與營運責任要由團隊承擔。

## 最短判讀路徑

判斷 Pyroscope deployment 是否健康、最少看四件事：

- **Agent / SDK setup**：是用 *language SDK*（in-process profiler、跟 application code 一起部署）還是 *Grafana Alloy / Pyroscope agent*（out-of-process、適合 binary-only 或無法改 code 的 workload）— 兩條路 overhead、覆蓋率、tag 注入方式都不同
- **Push or pull model**：SDK 預設 *push*（application 主動把 profile sample 推到 Pyroscope server）、Alloy / agent 可走 *pull*（scrape pprof endpoint、跟 Prometheus 同模型）— push 適合 short-lived job / serverless、pull 適合 long-running service + Kubernetes service discovery
- **Grafana integration**：是否在 Grafana datasource 設好 Pyroscope、explore 是否能跨 trace / log / profile 跳轉（Tempo trace → Pyroscope profile by service+span）、dashboard 是否內嵌 flame graph panel
- **Tag schema discipline**：service / version / region / environment / pod 是否一致命名、deploy event 是否打 label 讓 baseline / candidate 比較可成立

四件事任一缺失、profile 就只是「能看 flame graph」而非「release gate evidence」、無法支撐 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 的 diff workflow。

## 適用場景

自管 profiling backend 適合 Pyroscope。團隊若有資料主權、成本控制、內網部署或 OSS-first 要求，可以用 Pyroscope 保存 profile，降低 profile sample 外送帶來的治理成本。

Profile diff workflow 適合 Pyroscope。Release candidate、canary、baseline review 或 incident after-action 都可以用時間區間比較，找出 CPU、memory 或 allocation 的相對變化。

Grafana stack 整合適合 Pyroscope。若服務已經有 Grafana dashboard，profile link 可以放進 latency、CPU、memory、cost 或 release dashboard，讓 SRE 從聚合訊號跳到 callstack。

## 選型判準

| 判準            | Pyroscope 的價值                          | 需要補的能力                        |
| --------------- | ----------------------------------------- | ----------------------------------- |
| OSS / self-host | profile 資料可自管                        | backend storage、retention、upgrade |
| Grafana 整合    | dashboard、explore、profile link 容易串接 | tag schema 與 dashboard discipline  |
| Profile diff    | 時間區間與版本對比直觀                    | deploy label 與 baseline 管理       |
| 多語言 agent    | 常見 runtime 可導入                       | agent overhead 與覆蓋差異量測       |

OSS / self-host 價值來自控制權。Profile 可能包含 function name、package path、tenant-specific code path 或敏感 business logic，自管能讓資料保存與存取控制更貼近內部規範。

Grafana 整合價值來自操作連續性。當 CPU dashboard、latency dashboard 與 deploy annotation 都在 Grafana 中，Pyroscope 能讓工程師從圖表直接切到 flame graph。

## 跟其他工具的取捨

Pyroscope 和 Datadog Continuous Profiler 的主要差異是平台責任。Pyroscope 偏 OSS / self-host / Grafana stack；Datadog 偏 SaaS all-in-one 與 APM product workflow。

Pyroscope 和 Parca 的主要差異是生態定位。Pyroscope 偏 Grafana profiling backend 與 developer-facing flame graph；Parca 偏 eBPF / infrastructure-wide profiling 與 CNCF 生態。

Pyroscope 和一次性 profiler 的主要差異是可比較性。一次性 profiler 擅長局部調查；Pyroscope 擅長讓 profile 成為 release baseline 與 incident evidence。

## 核心取捨表

| 取捨維度      | Pyroscope（Grafana）                             | Parca                                          | Datadog Continuous Profiler               |
| ------------- | ------------------------------------------------ | ---------------------------------------------- | ----------------------------------------- |
| 部署模型      | OSS self-host / Grafana Cloud Profiles SaaS      | OSS self-host（CNCF Sandbox）                  | SaaS only                                 |
| Profile 來源  | language SDK + Alloy / agent（push 為主）        | pprof scrape（pull）+ Parca Agent（eBPF）      | Datadog Agent + language tracer 整合      |
| 語言覆蓋      | Go / Python / Java / Ruby / .NET / Rust / Node   | 任何能輸出 pprof 的 runtime + eBPF system-wide | Go / Python / Java / Ruby / .NET / Node   |
| Tag / label   | Prometheus-style label + 自訂 tag                | Prometheus-style label                         | Datadog tag（跟 APM 共用）                |
| Diff workflow | 時間區間 + label 對比 + flame graph diff UI      | 時間區間 + label 對比                          | 自動跟 deploy event + trace span 關聯     |
| 整合方向      | Grafana（Tempo / Loki / Mimir 互跳）             | Prometheus / Grafana（弱整合）                 | Datadog APM / Logs / Metrics 同 plane     |
| 適合場景      | Grafana-first、OSS-friendly、release diff 主流程 | infrastructure-wide eBPF profiling、CNCF 生態  | Datadog 已是主 observability、要 APM 連動 |

選 Pyroscope 的核心訴求：*已用 Grafana stack + 多語言服務組合 + 要 OSS self-host 選項或預算敏感*、profile 主要用途是 release diff / incident hot-path 定位、不需要 APM-level 自動 trace 關聯。

## 操作成本

Pyroscope 的主要成本是自管 backend。Profile ingest、storage、retention、compaction、backup、upgrade 與 dashboard ownership 都需要團隊負責。

Tag 成本來自查詢維度。service、version、region、environment、runtime、pod、tenant 這些 label 能提高定位能力，也會增加 cardinality、儲存與查詢成本。

Agent 成本來自 rollout 與 overhead。導入時要先選代表性服務，量測 profiler 對 CPU、memory、latency 的影響，再逐步擴大到 critical path。

## Evidence Package

Pyroscope 結果應回寫到 evidence package。最小欄位包括 service、version、environment、profile type、baseline window、candidate window、profile diff link、tag set、retention policy、overhead estimate、known gap 與 owner。

| 欄位         | Pyroscope 證據來源                       |
| ------------ | ---------------------------------------- |
| Source       | profile query、flame graph、diff link    |
| Time range   | baseline / candidate profile window      |
| Query link   | Grafana / Pyroscope explore link         |
| Data quality | tag completeness、sampling status        |
| Confidence   | production coverage、agent overhead      |
| Known gap    | 未覆蓋 runtime、tag drift、retention gap |

Evidence package 的核心用途是讓 profile diff 成為 release artifact。Reviewer 要能從 release gate 打開 Pyroscope diff，確認變化來自 code path、runtime 行為、負載變化或 baseline drift。

## 進階主題

**Grafana Cloud Profiles**：商業 SaaS 版本、走 Grafana Cloud 計費（per-series 或 per-profile bytes）、適合不想自管 storage / retention / compaction 的團隊。跟 OSS Pyroscope 共用 SDK 跟 query API、可在 OSS 起步、規模到一定程度再遷移到 Cloud、避免廠商一開始就鎖死。

**Flame graph diff**：Pyroscope 的核心 release workflow — 選 baseline window（release 前 24hr）跟 candidate window（release 後 24hr）、UI 把兩張 flame graph 差異標紅綠、可直接看到哪個 function 變慢 / 變快。判讀要點是 *baseline window 要排除部署當下的 warm-up / cache miss spike*、否則 diff 噪音蓋過真實 regression。

**多語言 SDK 覆蓋**：Pyroscope 官方 SDK 覆蓋 Go / Python / Java / Ruby / .NET / Rust / Node.js — Go SDK 用 `runtime/pprof` 包裝、Java 走 async-profiler、Python 走 `py-spy` 風格 sampling profiler、Node.js 走 V8 sampling。各 SDK overhead 不一致（Java async-profiler ~1%、Python py-spy ~3-5%）、選型時要看代表性服務量測再 rollout、不能假設「都很低」。

**Adhoc profiling**：當 production SDK 沒裝、或想對 batch job / CLI tool 做一次性 profile、可用 Pyroscope CLI 上傳 *standalone pprof file*（`pyroscope adhoc` 或 `profilecli`）— 補位「標準 pprof endpoint 不夠用、但又不想長期 instrument」的情境。對 ad-hoc incident investigation 跟 batch job postmortem 特別有用。

**Grafana Alloy 整合**：Grafana Alloy（前 Grafana Agent）內建 Pyroscope receiver、可同時 scrape Prometheus metrics + tail Loki log + push Tempo trace + scrape Pyroscope profile、單一 agent 跨 four signal、降低 sidecar 數量跟維運成本。

## 排錯與失敗快速判讀

- **SDK overhead 過高 / latency p99 上升**：profile sample rate 太高、或 Java async-profiler 在低 CPU host 競爭 schedule — 降 sample rate、staging 量測 CPU / latency delta 確認 < 3% 再 promote
- **Push agent 跟 pull agent 取捨錯**：short-lived job 用 pull 結果還沒被 scrape 就 exit、long-running service 用 push 結果 Pyroscope server 過載 — short-lived / serverless 走 SDK push、long-running + Kubernetes service discovery 走 Alloy pull
- **Label cardinality 爆 / storage 跟查詢都慢**：tag 加了 pod name / request ID / user ID 等高 cardinality 維度 — 限制 tag 為 service / version / region / environment / cluster 等低 cardinality、高基數維度走 trace / log 別放 profile
- **Baseline / candidate diff 全是噪音**：baseline window 沒對齊流量模式（off-peak vs peak）、或 deploy label 沒打 — 要求 release pipeline 自動寫 `version` / `deploy_id` label、diff window 跨完整流量週期（24hr or 7day）
- **Grafana datasource 連不到 / explore 跳轉失敗**：datasource URL 設錯、或 service / span tag 不一致 — Tempo trace 用的 `service.name` 要跟 Pyroscope `service` label 對齊、否則 cross-signal 跳轉斷裂
- **Storage / retention 失控**：profile 保留太久、SmartStore-like 冷儲存沒設 — Pyroscope OSS 支援 object storage（S3 / GCS）backend、長 retention 必開、不然 PV 會爆

## 何時改走其他服務

| 需求形狀                                       | 改走                                                                                                 |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 已用 Datadog APM、要 trace ↔ profile 自動關聯  | [Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/) |
| 要 eBPF system-wide / infrastructure profiling | [Parca](/backend/09-performance-capacity/vendors/parca/)                                             |
| 不想自管 backend、但要 Grafana stack           | Grafana Cloud Profiles（商業 SaaS、同 SDK）                                                          |

## 案例回寫

Pyroscope 適合回寫 OSS observability 與 release diff 案例。它可接 [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 profile noise 降低、[9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的 hot path 定位、[9.C12 Riot Games EKS multi-cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的 single-tenant per game profile 隔離、[9.C19 Capcom 遊戲後端](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 的 30% 成本下降 hot path 分析，以及 [9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 的 baseline / candidate profile diff。

這些案例的重點是可比較 profile。Pyroscope 頁引用案例時，要把 case 轉成 tag schema、baseline window、candidate window、flame graph diff 與 release gate evidence — 例如 Riot Games 246 cluster 的 tag schema 必須涵蓋 game / region / cluster 三維、才能避免「跨遊戲混合 profile」的歸因錯誤。

## 下一步路由

- 上游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 上游：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)
- 跨模組：[4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 平行：[Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/)
- 平行：[Parca](/backend/09-performance-capacity/vendors/parca/)
- 官方：[Grafana Pyroscope documentation](https://grafana.com/docs/pyroscope/latest/)
