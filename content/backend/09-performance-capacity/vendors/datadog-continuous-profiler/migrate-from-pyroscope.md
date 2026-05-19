---
title: "Pyroscope → Datadog Continuous Profiler：profiling deployment lifecycle 五階段、operational ownership 轉手"
date: 2026-05-19
description: "Pyroscope → Datadog Continuous Profiler 是 Type C operational hybrid migration — pprof data model 接近、profile lifecycle 五階段（install / instrument / ingest / query / cost）的 ops ownership 從 self-host 轉到 SaaS。本文走 6 維 audit（Operational High 其他 Low）、4-phase migration（operational audit + agent parallel + tag reconcile + cutover）、5 production 踩雷（agent 重複 overhead / tag schema 不一致 / trace_id correlation 斷 / cost 突增 / retention 政策變動）、何時保留 Pyroscope（資料主權 / 內網 / OSS-first / cost sensitive）"
tags: ["backend", "performance", "capacity", "vendor", "migration", "type-c", "operational-hybrid"]
---

Continuous profiling deployment 的 lifecycle 有五階段：**install**（agent / SDK 部署） → **instrument**（service / env / version tag 注入） → **ingest**（profile sample 進 backend store） → **query**（flame graph / diff / explore） → **cost**（storage retention / billing）。Pyroscope 跟 Datadog Continuous Profiler 在這五階段的 *ops ownership 分布完全不同*：

| 階段       | Pyroscope（self-host）                                       | Datadog Continuous Profiler                          |
| ---------- | ------------------------------------------------------------ | ---------------------------------------------------- |
| Install    | Grafana Alloy / Pyroscope agent / per-language SDK、自己部署 | Datadog Agent（多半 APM 已部署）、SDK 加 flag        |
| Instrument | tag schema 自己設計                                          | 用 Datadog 既有 `service` / `env` / `version` tag    |
| Ingest     | Pyroscope server（自管 storage / scaling）                   | Datadog SaaS（vendor 管）                            |
| Query      | Grafana datasource explore / flame graph panel               | Datadog APM 介面、跟 trace / log / metrics deep link |
| Cost       | self-host TCO（storage + ops + on-call）                     | 按 APM host 計費（profiling 是 add-on）              |

從 Pyroscope 遷出 Datadog Continuous Profiler 的本質是 *operational ownership 從 self-host 轉手到 SaaS* — pprof data model 跟 flame graph 視覺幾乎一樣、profile diff workflow 接近、*差異 90% 在 ops 跟 ecosystem integration*。schema / paradigm 差距小、operational 差距大、就是 Type C operational hybrid 的 signature。

## 為什麼是 Type C（operational 為主）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#6-維-diff-dimension-audit)：

| 維度        | 評         | 說明                                                              |
| ----------- | ---------- | ----------------------------------------------------------------- |
| Schema      | Low-Medium | pprof 是 industry standard、profile types (CPU / heap / etc) 接近 |
| Operational | High       | self-host backend storage / retention / scaling → SaaS 全託管     |
| Paradigm    | Low        | 都是 pprof-based continuous profiling、diff workflow 接近         |
| Components  | Low-Medium | 都需要 agent + backend、元件數量接近                              |
| App change  | Low        | agent / SDK config 改、code instrumentation 接近                  |
| Topology    | Low        | 都是 agent → backend 單向 ingest                                  |

Operational = High（其他 Low） → **Type C operational hybrid**。Type C 結構是 *operational audit prefix + 4-phase drop-in cutover* — operational diff 集中在 ingest / cost / retention 三階段、其他階段是 schema-level drop-in。

## Driver：TCO + Datadog ecosystem 內 deep linking

從 Pyroscope 遷出 Datadog Profiler 的核心 driver 有兩條：

**TCO（total cost of ownership）**：self-host Pyroscope 看起來免費（Apache 2.0）、但實際 ops 成本：

- Storage：profile sample 大、retention 與 storage cost 需要自己估（每 service 每天可能 1-10 GB）
- Scaling：profile ingestion 突增（deploy event / canary rollout 期間）要 storage / ingester 撐住
- On-call：Pyroscope server 自己會壞、要 on-call 帶
- Ops engineer time：規模成長後可能需要 0.5-1 個 FTE 維護 Grafana stack 內的 Pyroscope

對 *已經有 Datadog APM 帳單* 的 org、profiling 會跟 APM / profiled host 進同一個商務談判與 usage report，不需要額外 ops headcount。這條 TCO 拉力對 50-500 人 eng 規模最強 — 小於 50 人 self-host 也撐得住、大於 500 人 self-host 的 economy of scale 可能開始 favored Pyroscope。

**Ecosystem deep linking**：Datadog Profiler 跟 trace / log / metrics *在同一個介面*、profile span 直接連到 trace span、deploy marker 直接顯示在 flame graph timeline、cross-signal query 不用 wire。Pyroscope 要透過 Grafana datasource correlation 達到類似效果、但需要 Tempo / Loki 已部署 + 手動配 correlation rule、整合精度跟自動程度都不如 Datadog 內建。

這條 driver 對 *已是 Datadog-heavy org* 強、對 *Grafana-heavy org* 弱（後者 Pyroscope 才是自然選擇、Datadog Profiler 反而 ecosystem misfit）。

## Type C migration（4-phase）

### Phase 1：Operational audit

確認 Datadog Continuous Profiler 能 cover Pyroscope 當前用途、且 ops ownership 轉移可接受：

- **Language coverage**：當前 Pyroscope 用哪些 SDK？Datadog Profiler 支援 Go / Java / Python / Node / Ruby / .NET / PHP / Rust / C / C++，但每個語言的 profiler type 與啟用方式不同；Erlang 等較小眾語言仍要逐項驗證
- **Profile type coverage**：Pyroscope 抓的 profile type（CPU / heap / allocation / goroutine / lock / wall time）在 Datadog Profiler 同語言是否都支援？Java 跟 Go 兩家都全、其他語言可能 partial
- **Retention requirement**：Pyroscope retention 可自管；Datadog Profiler retention 依產品資料保留政策與合約設定，要確認是否滿足既有 long-term baseline / audit 查詢需求
- **資料主權**：profile data 包含 application function name / line number、有時帶 customer data hint（function 名字暗示 customer-specific 邏輯）— 是否能 send to SaaS？
- **Cost forecast**：Datadog public pricing 以 profiled host / APM tier 計費，估算時要用實際 host 數、container density、APM plan 與 commit discount 跟 Pyroscope self-host TCO 比

完成標準：寫出「Datadog 能 cover、不能 cover、不確定」三欄、不確定欄全部問過 Datadog SE / 用 trial 跑過 production-like load。

### Phase 2：Agent parallel run（profile 雙寫）

Datadog Agent 多半已部署（如果在用 Datadog APM）。Phase 2 在現有 Datadog Agent 開 profiling flag、*不關 Pyroscope agent*、跑 2-4 週 parallel：

- 設定 `DD_PROFILING_ENABLED=true`（per service env var）
- 每個 service SDK init 加對應 profiling enable call（Go: `profiler.Start()`、Python: `import ddtrace.profiling.auto`、Java: agent flag 即可）
- Pyroscope SDK / Alloy 繼續跑、profile 雙寫到兩家
- 對比同一個 service / 同一個時間段在 Pyroscope flame graph 跟 Datadog Profiler flame graph、確認 hot path 一致

Parallel run 期間的 overhead：兩邊 agent 同時跑 profiling、CPU overhead 大致 2-4%（單一 profiler 通常 1-2%、雙寫 double）、production-acceptable but not free。Phase 2 不要超過 4 週、避免長期 double overhead。

完成標準：每個 production service 在 Datadog Profiler 都有 4 週連續 profile data、跟 Pyroscope flame graph 對比一致。

### Phase 3：Tag schema reconcile + trace correlation

Pyroscope tag schema（自己設計）跟 Datadog standard tag（`service` / `env` / `version` / `host`）對齊：

- Pyroscope tag `app=checkout-api` → Datadog `service:checkout-api`
- Pyroscope tag `env=prod-us` → Datadog `env:prod` + `region:us-east-1`
- Pyroscope tag `git_sha=abc123` → Datadog `version:abc123`（透過 `DD_VERSION`）
- Custom tag（team / business unit）→ Datadog custom tag（透過 SDK config 或 agent label）

Trace correlation：Datadog Profiler 自動跟 APM trace 關聯（透過 `trace_id` injection into profile sample）— Phase 3 要驗證這個 correlation 可用（在 Datadog APM 點 trace span、應該能跳到對應時段 profile）。

Deploy marker：CI 在 deploy 時打 Datadog deployment marker（`datadog-ci deployment mark` 或 API call）、讓 Profiler diff view 知道 baseline / candidate 邊界。

完成標準：tag schema 1:1 對應、trace → profile deep link 可用、deploy marker 自動推送。

### Phase 4：Pyroscope agent 關掉 + server 退役

逐步關 Pyroscope agent（per service rollout）：

- 先關低重要性 service（dev / staging / non-critical prod）
- 觀察 1-2 週、確認沒事故再關下一批
- 最後關 critical service、留 Pyroscope server 跑 1-2 週空 ingest（rollback 緩衝）
- 取消 Pyroscope server（decommission storage、release K8s resource、關 on-call rotation）

Pyroscope 歷史 profile data 保留策略：

- 多數場景：直接 archive S3 / GCS、未來查得到但不維護 query UI
- 強合規場景：export Pyroscope flame graph data 為 pprof file 保存（pprof 是長期可讀格式）

完成標準：所有 production service 只走 Datadog Profiler、Pyroscope server 取消、TCO 對比驗證符合預期。

## 5 個 production 踩雷

### 1. 兩家 agent 同時跑造成 production overhead

Phase 2 parallel run 期間 CPU overhead 2-4%、預期內。但有些 service 設定錯誤（例如 sampling rate 預設都拉高）變成 6-10% overhead、p99 飄升、誤判為 Datadog Profiler 自己的問題。修法是 *parallel run 期間 Pyroscope sampling rate 降低 50%*（已經有歷史 baseline、不需要全採）、且 Phase 2 不要在 peak event 期間跑。

### 2. Tag schema 不一致導致 historic baseline 對不上

Pyroscope tag `app=checkout-api` 跟 Datadog `service:checkout-api` 都指同一個 service、但 Datadog 內 *historic profile* 沒有 `app` tag、所以從 Pyroscope 視角看 baseline 跟 Datadog 視角看 baseline *是不同的時段切片*。Release regression 比較時用錯 baseline、會誤判 release 沒問題（實際 baseline 不對應）。修法是 Phase 3 明確記錄 *Datadog Profiler 的 baseline 起算時間是 Phase 2 開始日*、Pyroscope 歷史不直接搬入比較。

### 3. Trace_id correlation 斷（Phase 3 最常見）

Datadog Profiler 自動關聯 trace 的前提是 *同一個 Datadog Agent + APM SDK 注入 trace_id*。如果 service 用 OpenTelemetry SDK + Datadog Agent（OTel-first 配置）、trace_id 注入方式不同、profile 跟 trace 可能無法自動 correlate。修法是 *確認所有 service 用 Datadog SDK 或正確配 OTel-to-Datadog converter*、在 Datadog APM 介面 random 抽 10 個 trace 驗證 profile correlation 是否 wire 通。

### 4. Cost 突增（Phase 4 後常見）

關掉 Pyroscope agent 後、Datadog Profiler 變成 sole profile source、ingest volume 上升、Datadog bill 比預估高 30-50%。原因通常是：

- Profile sampling rate 不小心開太高（部分 service config 沒對齊）
- Custom tag 太多（每個 unique tag combination 增加 indexing cost）
- Profile event 量比預估高（service count × sampling rate × profile types）

修法是 Phase 1 cost forecast 要保留 30% buffer、且 Phase 4 完成後立即跑 Datadog usage report 確認 actual 跟 forecast 對比。

### 5. Retention / baseline 政策變動造成歷史 query 斷層

Pyroscope 自管 retention 可以設成配合內部 storage 與 compliance policy；Datadog Profiler 的 retention 依產品資料保留政策與合約設定。真正的風險不是固定「7 天 vs 90 天」，而是 *既有 baseline 查詢習慣是否還成立*：原 Pyroscope user 可能習慣查特定 release 前後的 flame graph、Datadog 端則要看 profile tag、deployment marker 與保留政策能否支援同樣查詢。修法是 Phase 1 明確列出「要查多久前、用什麼 tag 找、誰有權限看」三個問題，超出 profile retention 的長期 trend 改用 Datadog metrics-derived signal（cumulative CPU% / memory growth rate）或保留 Pyroscope archive。

## Capability 對照

| 能力                                    | Pyroscope（self-host）                               | Datadog Continuous Profiler                                      |
| --------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------- |
| Language SDK 覆蓋                       | Go / Java / Python / Node / Ruby / .NET / Rust / PHP | Go / Java / Python / Node / Ruby / .NET / PHP / Rust / C / C++   |
| Profile type（CPU / heap / lock / etc） | 全（依語言 SDK 而定）                                | 全（依語言 SDK 而定）                                            |
| Flame graph diff workflow               | Grafana panel                                        | Datadog Profile Comparison                                       |
| Trace correlation                       | 手動配 Grafana correlation rule                      | 自動（trace_id injection）                                       |
| Deploy marker                           | 手動                                                 | datadog-ci 自動                                                  |
| Retention                               | 自管（無上限、cost 自負）                            | 依 Datadog retention policy / 合約設定                           |
| 資料主權                                | 完全自管                                             | SaaS（profile 出境）                                             |
| Ops ownership                           | 自管（storage / scaling / on-call）                  | Vendor                                                           |
| Cost model                              | self-host TCO                                        | profiled host / APM tier / commit discount                       |
| Cross-signal query                      | Grafana cross-datasource                             | Datadog native（trace / log / profile / metrics 同一 query bar） |

## 何時不要切（保留 Pyroscope）

- **資料主權 / compliance 不允許 profile data 出境**：金融 / 醫療 / 政府 / 國防、保留 Pyroscope self-host
- **內網 / air-gap 部署**：物理上連不到 Datadog SaaS、保留 Pyroscope
- **OSS-first / vendor neutrality policy**：org 政策不允許 vendor lock-in profiling、保留 Pyroscope
- **規模超大（> 500 APM host）**：Datadog Profiler add-on cost × host 數可能超過 Pyroscope self-host TCO、計算交叉點
- **Long retention / 自訂 archive 強需求**：若 profile data 必須照內部 retention policy 長期保存、保留 Pyroscope 或建立 export / archive 流程
- **Datadog 不支援的語言或 profiler type**：Erlang、特定 runtime 或特定 profile type 若 Datadog 無法覆蓋，保留 Pyroscope 為對應 service profiling

## 下一步路由

- 平行 batch：[JMeter → k6](/backend/09-performance-capacity/vendors/k6/migrate-from-jmeter/)（Type E paradigm shift）
- 同 batch Type C：（待補、本篇是 batch 唯一 Type C）
- 上游：[9.8 Performance Observability](/backend/09-performance-capacity/performance-observability/) / [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 下游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)（profile diff 接入 release regression workflow）
- vendor 對照：[Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/) / [Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/) / [Parca](/backend/09-performance-capacity/vendors/parca/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type C operational hybrid 結構說明）
