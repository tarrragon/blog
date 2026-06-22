---
title: "Sentry"
date: 2026-05-01
description: "Error tracking 主流、APM / Profiling / Session Replay 擴展"
weight: 9
tags: ["backend", "observability", "vendor"]
---

Sentry 是 error tracking 的事實標準、承擔三個責任：跨 frontend / backend / mobile 的 unhandled exception 自動聚合（issue grouping）、release-aware error tracking（regressed errors / source map）、延伸功能（APM / Continuous Profiling / Session Replay / Cron Monitoring）。設計取捨偏向「錯誤生命週期管理 + UX 強 + OSS self-host 雙軌」、不追求 metrics / logs 全面平台。

## 本章目標

讀完本章後、你應該能：

1. 整合 Sentry SDK（auto-instrumentation）到 frontend / backend / mobile
2. 配置 release + source map、追蹤 regressed errors
3. 設計 issue grouping / fingerprint 避免 noise
4. 用 Sentry Performance / Session Replay / Cron Monitoring
5. 評估 self-hosted vs SaaS、跟 IR 平台整合

## 最短路徑：5 分鐘把 Sentry 跑起來

```bash
# 1. 註冊 Sentry / self-host、拿 DSN
# TODO: 從 Console 拿 project DSN

# 2. 整合 SDK（範例：Python）
# TODO: import sentry_sdk; sentry_sdk.init(dsn=..., traces_sample_rate=1.0)

# 3. 觸發 test exception 驗證
# TODO: try: 1/0 / except: sentry_sdk.capture_exception()
```

## 日常操作與決策形狀

### SDK 整合（auto-instrumentation）

子議題：

- 各語言 SDK：Python / Node / Java / Go / Ruby / PHP / .NET / iOS / Android
- 自動 framework instrumentation（Django / FastAPI / Express / Rails 等）
- Manual capture：`capture_exception` / `capture_message`
- 對應 OTel integration（Sentry 接受 OTel context）

### Release / source map

子議題：

- Release 標記每次部署（git SHA / version）
- Source map 上傳：minified frontend code → readable stack trace
- Regressed errors：之前 resolved 在新 release 又出現
- 對應 release health metric

### Issue grouping / fingerprint

子議題：

- Auto grouping：based on stack trace + exception type
- 自訂 fingerprint：把不同 errors 聚成同 issue
- 拆 issue：相同 stack 但需分開追蹤
- 對應 noise 控制

### Performance monitoring

子議題：

- Traces sampling rate
- Transaction / span 結構（類 APM）
- Web Vitals（前端 LCP / FID / CLS）
- 跟 OTel trace 互操作

## Deep Article

- [Error Grouping 與 Fingerprinting 策略](error-grouping-fingerprinting/)：預設 grouping 演算法、自訂 fingerprint rules、merge/unmerge、grouping 不準的判讀與大量 unique errors 的治理
- [Release Tracking 與 Session Replay](release-tracking-session-replay/)：release health、deploy tracking、session replay 隱私設定、performance monitoring 與 OTel 整合、self-hosted vs SaaS

## 進階主題（按需閱讀）

### Session Replay

子議題：

- 前端用戶體驗錄影（含 error 前後操作）
- 隱私設定：mask PII / block element
- Sample rate 控制
- 跟 LogRocket / FullStory 對照

### Cron Monitoring（Sentry Crons）

子議題：

- 監控 scheduled job 是否準時跑 + 是否成功
- Schedule 配置（crontab / interval）
- Heartbeat ping / 自動 alert
- 對應 [08 incident response](/backend/08-incident-response/)

### Continuous Profiling

子議題：

- 各語言 profiler（Python / Node / Go）
- CPU / memory flame graph
- 跟 Pyroscope / Datadog Profiler 對照

### Self-hosted vs SaaS

子議題：

- Self-hosted：Sentry OSS（docker-compose + 數十 service）
- SaaS：sentry.io、5 levels（developer / team / business / enterprise）
- 規模化通常用 SaaS（self-host 維運成本高）
- Privacy / compliance 場景：self-host

### 跟 IR 平台整合

子議題：

- 跟 PagerDuty / Opsgenie / incident.io 整合
- Alert routing：嚴重 issue → on-call
- Issue 跟 incident ticket 關聯
- 對應 [08 incident response 模組](/backend/08-incident-response/)

### OTel integration

子議題：

- Sentry SDK 接受 OTel context（trace_id / span_id）
- 跟其他 OTel backend dual ship
- Sentry 自家 SDK feature 較深（vs 純 OTel）

## 跟 Monitoring 模組的分工

本頁從 server-side 觀測平台角度說明 Sentry — error grouping 的告警整合、performance monitoring 的 SLI 指標設計、self-hosted vs SaaS 成本、跟 OTel 的 context 整合。Client-side 的使用體驗（SDK 自動攔截設計、error grouping 的 client 端行為、session replay 的操作重播、跟自架 monitor 的比較）見 [Monitoring 模組 Sentry 深入](/monitoring/06-commercial-comparison/sentry-deep-dive/)。

兩者的交叉點是 error event 的格式和 trace context propagation — client SDK 捕獲的 error 帶 trace context，server-side 的 Sentry 用同一個 trace 串接完整路徑。

## 排錯快速判讀

### Issue 不出現

操作原則：先確認 SDK 配置（DSN + initialization）、再看 sampling rate、最後看 ad blocker 等網路問題。

### Issue noise（太多 issue）

操作原則：用 fingerprint / inbound filter / rate limit 控制。判讀：Issue list 看哪些是噪音。

### Release 沒對應

操作原則：release tag 沒正確傳 SDK、或 source map 沒上傳。判讀：issue 沒有 release 資訊。

### Performance traces 缺失

操作原則：sampling rate 過低或 SDK 沒啟用 performance。

### Session Replay 不出現

操作原則：sample rate 設定 + 隱私 setting 是否 block 過頭。

## 何時改走其他服務

| 需求形狀                 | 改走                                                                                                                                     |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 完整 metrics / logs 平台 | [Datadog](/backend/04-observability/vendors/datadog/) / [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) / ELK          |
| High-cardinality 分析    | [Honeycomb](/backend/04-observability/vendors/honeycomb/)                                                                                |
| 純 backend 已有 APM      | 跟 [Datadog](/backend/04-observability/vendors/datadog/) APM 重疊、選一即可                                                              |
| 替代 error tracking      | Bugsnag / Rollbar / Raygun（T2 候選）                                                                                                    |
| Pure logs / metrics      | [Prometheus](/backend/04-observability/vendors/prometheus/) / [Elastic](/backend/04-observability/vendors/elastic-stack/) / Cloud-native |
| OTel-only 標準           | [OTel](/backend/04-observability/vendors/opentelemetry/) + 任一 backend                                                                  |

## 不在本頁內的主題

- 各語言 Sentry SDK 完整 API
- Sentry self-host 部署細節
- 各 framework integration 細節
- Sentry pricing 詳細

## 案例回寫

### 直接相關案例（待補 frontend Sentry case）

Sentry 是 04 observability 模組第二大 SaaS（次 Datadog）、但 04 cases 庫主要聚焦 OTel / Prometheus / Grafana / ELK 等後端 telemetry pipeline 場景、Sentry 直接案例（frontend error / release health）待補。

### 跨 vendor 對照

| 案例                                                                                                     | 對 Sentry 的對應                                   |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| [4.C1 Fintech audit](/backend/04-observability/cases/fintech-audit-evidence-observability/)              | Issue 跟 audit evidence 串聯、release 對應監管要求 |
| [4.C2 Gaming peak](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)        | 高峰下 issue noise / rate limit / inbound filter   |
| [4.C9 OTel migration signal drift](/backend/04-observability/cases/failure-otel-migration-signal-drift/) | Sentry SDK ↔ OTel context propagation 雙軌驗證     |
| [4.C10 規模對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)               | Frontend / mobile-heavy team 通常選 Sentry         |

**待補 frontend Sentry case**：大規模前端團隊（Shopify / Slack / GitHub frontend）error tracking 案例、release health 落地、跟 incident.io / PagerDuty 整合案例。

## 下一步路由

- 上游概念：[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 平行 vendor：[Datadog](/backend/04-observability/vendors/datadog/)、[OpenTelemetry](/backend/04-observability/vendors/opentelemetry/)
- 下游能力：[08 incident response 模組](/backend/08-incident-response/)
