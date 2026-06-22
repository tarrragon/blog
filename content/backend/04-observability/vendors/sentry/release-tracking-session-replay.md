---
title: "Sentry Release Tracking 與 Session Replay"
date: 2026-06-22
description: "說明 Sentry release health、deploy tracking、session replay 隱私設定、performance monitoring 與 OTel 整合、self-hosted vs SaaS 取捨"
weight: 11
tags: ["backend", "observability", "sentry", "release-tracking", "session-replay"]
---

> 本文是 [Sentry](/backend/04-observability/vendors/sentry/) 的 vendor deep article，深化 overview「Release / source map」跟「Session Replay」段。初次接觸 Sentry 的讀者建議先讀 [Sentry 服務頁](/backend/04-observability/vendors/sentry/)。

## 問題情境

Release tracking 讓 Sentry 從「error 收集器」升級成「部署品質追蹤器」。每次部署標記一個 release，Sentry 自動計算 crash-free sessions、regressed errors 跟 release health。Session Replay 進一步把 error 的觸發脈絡從 stack trace 擴展到使用者操作錄影。兩者搭配使用時，團隊能看到「這個版本部署後、哪些使用者遇到什麼操作導致什麼錯誤」的完整鏈路。

## Release Health

### 核心概念

Release health 追蹤每個版本的使用者體驗品質。核心指標：

| 指標                | 定義                                    | 健康閾值        |
| ------------------- | --------------------------------------- | --------------- |
| Crash-free sessions | 沒有 unhandled error 的 session 百分比  | 99.5% 以上      |
| Crash-free users    | 沒有遇到 unhandled error 的使用者百分比 | 99.5% 以上      |
| Adoption rate       | 使用此版本的 session 佔比               | 依 rollout 策略 |
| Error count         | 此版本的 error event 數量               | 不應比前一版高  |

Crash-free sessions 跟 crash-free users 的差異：sessions 是頻率加權（一個使用者一天開 10 次 app，10 次都算），users 是去重的。Mobile app 通常看 crash-free users（使用者感知），web 通常看 crash-free sessions（頻率反映服務品質）。

### Release 標記

在 SDK 初始化時傳入 release 標記：

```python
sentry_sdk.init(
    dsn="...",
    release="checkout-api@1.2.3",
    environment="production",
)
```

Release 命名慣例：`<service>@<version>` 或 git SHA。用語意版本方便比較，用 git SHA 方便對應 commit。CI/CD pipeline 在 deploy step 自動設定。

### Deploy 標記

Release 建立後，用 Sentry CLI 或 API 標記 deploy：

```bash
sentry-cli releases deploys checkout-api@1.2.3 new \
  --env production \
  --started $(date -u +%s) \
  --finished $(date -u +%s)
```

Deploy 標記讓 Sentry 知道某個 release 何時部署到哪個環境。issue list 的 "First seen in release" 跟 "Regressed in release" 依賴這個資訊。

### Regressed Error 偵測

Sentry 會追蹤已 resolve 的 issue。如果新 release 重新觸發了已 resolve 的 issue，Sentry 標記為 regression。這比人工追蹤有效 — 團隊不需要記住哪些 bug 修過，Sentry 自動偵測回歸。

Regression 通知的準確度取決於 grouping 品質。如果 grouping 不準（見 [Error Grouping 與 Fingerprinting](../error-grouping-fingerprinting/)），regression 偵測也會不準 — 不同 bug 被合成同一 issue 時，resolve 一個 bug 後另一個觸發會被誤判為 regression。

### Source map 上傳

前端 minified code 的 stack trace 不可讀。上傳 source map 讓 Sentry 還原原始 source code 位置：

```bash
sentry-cli releases files checkout-api@1.2.3 upload-sourcemaps \
  --url-prefix '~/static/js' \
  ./build/static/js
```

Source map 上傳必須在 deploy 前完成，且 release 版本跟前端 build 版本一致。版本不一致時，Sentry 找不到對應的 source map，stack trace 仍然是 minified。

CI/CD 整合：在 build step 之後、deploy step 之前上傳 source map。多數框架（Next.js、Vite、Webpack）有 Sentry plugin 自動處理。

## Session Replay

### 核心能力

Session Replay 錄製使用者在網頁上的操作。Sentry 記錄的是 DOM mutation 跟使用者事件的結構化資料，播放時 replay DOM 變化，效果類似影片但資料量遠小於螢幕錄影。

replay 跟 error 關聯：Sentry 在 error event 中附帶 replay ID，讓工程師從 issue detail 直接跳到 error 發生前後的使用者操作。

### 隱私設定

Session Replay 預設會遮罩敏感資訊：

| 遮罩類型 | 預設行為                             | 自訂方式                                                     |
| -------- | ------------------------------------ | ------------------------------------------------------------ |
| 文字內容 | 所有文字替換成 `*`                   | `maskAllText: false` 關閉、或用 CSS class `sentry-mask` 指定 |
| 輸入框   | 所有 input value 遮罩                | `maskAllInputs: false` 關閉（注意 PII 風險）                 |
| 圖片     | 不遮罩（但 `<img>` 從原始 URL 載入） | `blockAllMedia: true` 遮蔽所有媒體                           |
| 特定元素 | 不遮罩                               | 加 `data-sentry-block` attribute 完全隱藏                    |

PII 合規考量：

- 預設 `maskAllText: true` + `maskAllInputs: true` 是安全起點
- GDPR / CCPA 場景需要額外確認：replay 資料存在 Sentry SaaS（美國資料中心），跨境傳輸需要評估
- Self-hosted Sentry 可以把 replay 資料留在自己的基礎設施

### Sampling 策略

Session Replay 會增加前端 SDK 的 payload 大小跟 Sentry 的 event quota。用 sampling rate 控制：

```javascript
Sentry.init({
  dsn: "...",
  replaysSessionSampleRate: 0.1,  // 10% 的 session 錄影
  replaysOnErrorSampleRate: 1.0,  // error 發生時 100% 錄影
});
```

推薦策略：`replaysSessionSampleRate` 用低值（1-10%），`replaysOnErrorSampleRate` 用 100%。目的是確保每個 error 都有 replay 可看，但不錄所有正常 session。

高流量網站（每日百萬 session 以上）可能需要把 `replaysSessionSampleRate` 設到 0，只在 error 時才錄。session replay 的 quota 消耗速度可以在 Sentry Usage Stats 頁面監控。

## Performance Monitoring

### Transaction-based tracing

Sentry 的 performance monitoring 用 transaction / span 結構（跟 OpenTelemetry 的 trace / span 概念對齊）。每個 HTTP request、page load 或自訂操作是一個 transaction，transaction 內的子操作是 span。

```python
with sentry_sdk.start_transaction(op="checkout", name="POST /api/checkout"):
    with sentry_sdk.start_span(op="db", description="insert order"):
        # DB operation
        pass
    with sentry_sdk.start_span(op="http", description="payment gateway"):
        # External API call
        pass
```

自動 instrumentation 會自動建立 transaction 跟 span（HTTP framework、DB driver、HTTP client）。手動 span 用在自訂業務邏輯或自動 instrumentation 沒覆蓋的路徑。

### OTel context 整合

Sentry SDK 支援 OTel context propagation — 如果 upstream service 用 OTel SDK 產生 trace，Sentry SDK 會接受 `traceparent` header 中的 trace_id 跟 parent_span_id，把自己的 transaction 接到同一條 trace。

整合方式：

| 場景                         | 設定                                                            |
| ---------------------------- | --------------------------------------------------------------- |
| Sentry SDK 接收 OTel context | 預設支援 W3C Trace Context、不需額外設定                        |
| Sentry 資料送到 OTel backend | 用 Sentry 的 OTel exporter（experimental）                      |
| OTel SDK 送資料到 Sentry     | OTel SDK → OTLP exporter → Sentry（Sentry 支援 OTLP ingestion） |

常見架構：backend service 用 OTel SDK + Collector，frontend 用 Sentry SDK（前端 error tracking 跟 session replay 是 Sentry 的強項）。兩者透過 trace_id 關聯，在 Sentry 看 frontend error + replay，在 OTel backend 看 backend trace。

### Web Vitals

前端 SDK 自動收集 Core Web Vitals（LCP、FID / INP、CLS）跟 TTFB。這些指標跟 error 在同一個 dashboard，讓團隊在 release 後同時看 error regression 跟效能 regression。

Web Vitals 的觀測不需要額外設定 — 前端 SDK 自動收集。但 sampling rate 會影響資料量 — `tracesSampleRate` 設太低時，Web Vitals 的 sample 數量可能不夠做統計比較。

## Self-hosted vs SaaS

### 決策維度

| 維度               | SaaS（sentry.io）           | Self-hosted                          |
| ------------------ | --------------------------- | ------------------------------------ |
| 維運               | Sentry 負責                 | 自己維運（docker-compose、20+ 容器） |
| 資料位置           | Sentry 資料中心（美國為主） | 自己的基礎設施                       |
| 功能完整度         | 全功能                      | 社群版功能略少（部分企業功能不含）   |
| 升級               | 自動                        | 手動（每月有新版、升級需要停機）     |
| 成本模型           | Event-based pricing         | 基礎設施 + 人力成本                  |
| Replay / Profiling | 含                          | 含（但 storage 自負）                |

### 何時選 self-hosted

資料必須留在特定地理區域（GDPR / 特定產業法規）、或企業 security policy 不允許 error data 送到第三方 — 這是 self-hosted 的核心理由。

Self-hosted Sentry 的維運成本常被低估：20+ 個容器（Kafka、ClickHouse、PostgreSQL、Redis、Snuba、Relay 等）、升級可能需要資料庫 migration、troubleshooting 時沒有 vendor 支援。中小團隊通常 SaaS 的 event pricing 比 self-hosted 的人力成本低。

### 混合模式

部分團隊用混合模式：production error 送 Sentry SaaS（低維運），但 audit-sensitive 的資料（PII-heavy environment）走 self-hosted。兩套 Sentry instance 各自獨立，不共享 issue。

## 整合與下一步

- Error grouping 策略：在 issue 數量失控前建立 fingerprint rule，見 [Error Grouping 與 Fingerprinting](../error-grouping-fingerprinting/)
- 觀測證據整合：把 Sentry issue link 放進 evidence package，見 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- Client-side monitoring：Sentry 的前端 SDK 跟 RUM 的定位互補，見 [4.10 Client-side Monitoring](/backend/04-observability/client-side-monitoring/)
- 事故響應整合：Sentry alert → PagerDuty / incident.io，見 [08 Incident Response 模組](/backend/08-incident-response/)
