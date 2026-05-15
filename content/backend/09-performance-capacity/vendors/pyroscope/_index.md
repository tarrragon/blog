---
title: "Pyroscope"
date: 2026-05-15
description: "用 Grafana 生態與開源 profiling backend 建立可自管 profile diff 與 flame graph 的工具"
weight: 31
tags: ["backend", "performance", "capacity", "vendor", "pyroscope", "profiling"]
---

Pyroscope 的核心責任是提供開源 continuous profiling backend，讓團隊用 Grafana 生態保存、查詢、比較與視覺化 production profile。它適合偏 OSS-first、已使用 Grafana / Prometheus / Tempo / Loki 的團隊，重點在把 CPU、memory、allocation 與 profile diff 放進可自管 observability stack。

## 定位

Pyroscope 適合 Grafana-first 的 profiling 路線。當團隊已經用 Grafana 做 dashboard、Prometheus / Mimir 做 metrics、Tempo 做 traces、Loki 做 logs，Pyroscope 可以補上 profiling 這一角，讓 flame graph 與 profile diff 進入同一套查詢與權限流程。

這個定位讓 Pyroscope 接到 [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/) 與 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)。它的價值在於 OSS / Grafana 整合與可自管；它的代價在於 storage、retention、agent rollout 與營運責任要由團隊承擔。

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

## 案例回寫

Pyroscope 適合回寫 OSS observability 與 release diff 案例。它可接 [Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 profile noise 降低、[Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的 hot path 定位，以及 [9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 的 baseline / candidate profile diff。

這些案例的重點是可比較 profile。Pyroscope 頁引用案例時，要把 case 轉成 tag schema、baseline window、candidate window、flame graph diff 與 release gate evidence。

## 下一步路由

- 上游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 上游：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)
- 跨模組：[4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 平行：[Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/)
- 平行：[Parca](/backend/09-performance-capacity/vendors/parca/)
- 官方：[Grafana Pyroscope documentation](https://grafana.com/docs/pyroscope/latest/)
