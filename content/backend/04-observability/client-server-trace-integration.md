---
title: "4.24 Client-to-Server 端到端觀測串接"
date: 2026-06-22
description: "用一個結帳場景走完 browser click → trace context → server span → 統一 waterfall 的完整實作鏈路"
weight: 24
tags: ["backend", "observability", "tracing", "rum", "client-server"]
---

Client-to-server 端到端觀測串接的核心責任是讓一次使用者操作的完整路徑 — 從 browser click 到 server 處理到 response rendering — 可以用同一個 trace ID 串起來。[4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/) 講的是概念和 vendor 定位；本篇走完一個具體場景的實作鏈路。[Monitoring 模組 03 SDK 設計](/monitoring/03-sdk-design/) 講的是 client 端怎麼埋點；本篇講 server 端怎麼接收和整合。

## 完整鏈路

以使用者在 web app 點擊「結帳」為例，一次操作產生的觀測鏈路：

```text
Browser: user clicks "checkout"
  → RUM SDK 建立 client span（type: resource / xhr）
  → HTTP POST /api/checkout + W3C traceparent header
    → Server middleware 提取 trace context
    → Server 建立 child span（checkout-handler）
      → DB query span（order insert）
      → Cache span（inventory check）
      → Queue span（event publish）
    → Server 回 200 + response body
  → Browser 收到 response → resource timing 結束
  → RUM SDK 關閉 client span（記錄 duration + status）
  → 統一 trace waterfall：client span 是 root、server spans 是 children
```

鏈路的每一段都需要 trace context 正確傳遞。任何一段斷掉，trace waterfall 就會出現孤立的 span — server 端看到的 trace 跟 client 端看到的 trace 是兩條不相關的紀錄。

## Trace context propagation

### W3C traceparent header

W3C Trace Context 是跨 vendor 的標準 propagation 格式。Header 長這樣：

```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              │  │                                │                  │
              │  trace-id (32 hex)                 parent-id (16 hex) flags
              version
```

RUM SDK 在發起 XHR / fetch 時把 `traceparent` 注入 request header。Server 的 trace SDK 從 header 提取 trace-id 和 parent-id，建立 child span。

### Client 端注入

各 RUM SDK 的注入方式：

| SDK              | 注入機制                                                                         | 配置                                                |
| ---------------- | -------------------------------------------------------------------------------- | --------------------------------------------------- |
| Datadog RUM      | 自動 patch XHR / fetch，注入 `x-datadog-*` + 可選 `traceparent`                  | `allowedTracingUrls` 設定允許注入的 domain          |
| Sentry browser   | 自動 patch fetch / XHR，注入 `sentry-trace` + `baggage` + 可選 `traceparent`     | `tracePropagationTargets` 設定目標 URL              |
| OTel browser SDK | 透過 `XMLHttpRequestInstrumentation` / `FetchInstrumentation` 注入 `traceparent` | `propagateTraceHeaderCorsUrls` 設定 CORS 允許的 URL |

三者的共同模式：只對設定的 domain 注入 trace header。不設定白名單時，header 不會被注入到第三方 API（避免 information leakage）。

### Server 端提取

Server 端的 trace SDK（OTel auto-instrumentation 或 vendor agent）從 incoming request 的 header 提取 trace context：

```python
# OTel Python 範例 — auto-instrumentation 自動處理
# 不需要手動提取，middleware 自動讀 traceparent header
# 建立的 span 會繼承 client 傳來的 trace-id 和 parent-id

# 手動提取（不用 auto-instrumentation 時）
from opentelemetry.propagate import extract
ctx = extract(carrier=request.headers)
with tracer.start_as_current_span("checkout-handler", context=ctx):
    # server logic
    pass
```

### CORS 限制

跨域請求時，browser 的 CORS preflight 會阻止非標準 header。Server 需要明確允許 trace header：

```text
Access-Control-Allow-Headers: traceparent, tracestate, sentry-trace, baggage
```

CORS 是 client-server trace 串接最常見的斷裂原因。Server 沒有回 `Access-Control-Allow-Headers: traceparent` 時，browser 會 strip 掉 trace header，server 端收到的 request 沒有 trace context，建立的 span 成為新的 root — 跟 client span 斷裂。

## 跨層 correlation 設計

### Trace ID 串接

統一 trace-id 是最基本的 correlation。同一個 trace-id 下的所有 span（client + server）可以在 trace backend 的 waterfall view 裡按時間排列，看到完整的 request 路徑。

### Session 跟 transaction 的 mapping

RUM SDK 的 session（使用者的一次造訪）包含多個 user action，每個 action 可能觸發多個 HTTP request。Mapping 關係：

```text
RUM session
  └── user action (click "checkout")
        ├── HTTP request /api/checkout  →  server transaction (trace)
        ├── HTTP request /api/inventory →  server transaction (trace)
        └── client-side rendering time
```

Datadog RUM 和 Sentry 都支援從 session replay 點進去看對應的 server trace。這個 mapping 靠的是 RUM event 裡記錄的 trace-id，跟 server trace backend 裡的同一個 trace-id 做 join。

### Breadcrumbs 跟 server log 的時間對齊

RUM SDK 收集的 breadcrumbs（使用者操作序列：page view → button click → form submit）跟 server-side log 的 timestamp 需要可比對。時間對齊的前提是 client 和 server 的 clock 差距在可接受範圍（通常 < 1s）。

NTP 同步的 server 端 clock 通常精準。Client 端（browser）依賴使用者裝置的系統時間，可能偏差數秒到數分鐘。RUM SDK 通常會記錄 relative timing（相對於 session 開始的 offset），而非絕對 timestamp，來降低 clock skew 的影響。

### Error correlation

Client-side JS error 跟 server-side 5xx 可能是同一個問題的兩面。Correlation 方式：

- **同一 trace-id**：client error 發生在某個 HTTP request 的 response 處理中，該 request 的 trace-id 跟 server-side 500 的 trace-id 相同 — 直接 correlation
- **時間窗 + endpoint**：client error 沒有 trace-id（例如 CORS block 導致 request 沒發出），用時間窗 + endpoint 模式做 fuzzy correlation
- **Server 無異常但 client 報錯**：client-side rendering error（JSON parse failure、type error），server 端看不到 — 需要 RUM 獨立分析

## Evidence package 整合

把 client-side 訊號納入 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 時，需要額外記錄：

| 欄位       | Client-side 補充                                                  | 為什麼需要                                                   |
| ---------- | ----------------------------------------------------------------- | ------------------------------------------------------------ |
| Source     | 標註 "RUM" 或 "Synthetic"                                         | 區分 server-side metrics 和 client-side metrics              |
| Latency    | Client perceived latency（含 DNS + network + server + rendering） | 跟 server-side latency 差異是 network + rendering 時間       |
| Known gap  | Trace sampling 不一致                                             | Client 和 server 可能各自取樣，同一個 request 不一定兩邊都有 |
| Confidence | Client clock skew 可能影響 timestamp precision                    | 標注 client timestamp 的精確度限制                           |

Client perceived latency 跟 server-side latency 的差異本身就是一個觀測訊號。差異穩定在 50ms 是正常的 network overhead；差異突然從 50ms 跳到 500ms 代表網路或 CDN 出了問題 — 而這個問題 server-side dashboard 完全看不到。

## 失敗場景判讀

| 失敗訊號                                  | 判讀                                                                                        | 下一步                                                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Client span 存在但 server span 缺失       | Trace context header 沒被 propagate — 最常見原因是 CORS block                               | 檢查 `Access-Control-Allow-Headers` 是否包含 `traceparent`；檢查 RUM SDK 的 `allowedTracingUrls` 設定 |
| Server 正常但 client perceived latency 高 | 網路延遲或 client rendering 慢                                                              | 看 RUM 的 resource timing breakdown（DNS / TCP / TLS / TTFB / download / render）                     |
| Client error 但 server 無對應 request     | Request 沒發出 — client-side validation 擋掉或 network offline                              | 看 RUM breadcrumbs 確認 request 是否有送出；檢查 navigator.onLine 狀態                                |
| Trace sampling 不一致                     | Client 取樣到但 server 沒取樣到同一個 request                                               | 統一 sampling decision — 用 head-based sampling（decision 在 trace 起點做、propagate 到下游）         |
| Client 和 server 的 error count 對不上    | Client 包含 JS rendering error（server 看不到）；server 包含非 user-facing 的背景 job error | 分開看：API error 用 trace correlation 比對、non-API error 各自歸類                                   |

## Vendor 整合模式

| 組合                                    | 串接方式                                                     | 限制                                                          |
| --------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------- |
| Datadog RUM + Datadog APM               | 原生 — 同一個 Datadog org 裡 client 跟 server trace 自動關聯 | 兩邊都要 Datadog plan                                         |
| Sentry browser + Sentry server          | 原生 — `sentry-trace` header propagation                     | Performance monitoring 需要 Sentry paid plan                  |
| OTel browser SDK + OTel server SDK      | W3C `traceparent` — vendor-neutral 標準                      | Browser SDK 較新、instrumentation 覆蓋度不如 server 端成熟    |
| 混合（Sentry browser + Datadog server） | 手動橋接 — 確保雙方都支援 W3C `traceparent`                  | Trace context format 要一致；session-level correlation 需自建 |

同 vendor 組合的串接最自然。跨 vendor 組合只要雙方都支援 W3C Trace Context，trace-level correlation 可以通；但 session-level 的功能（session replay → server trace）需要同 vendor 才有。

## 交接路由

- [4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/)：概念定位和 vendor 選型
- [4.3 Tracing Context](/backend/04-observability/tracing-context/)：server-side trace context 設計
- [4.22 Checkout API Evidence Package](/backend/04-observability/checkout-api-evidence-package/)：evidence 整合到 release gate
- [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)：evidence 欄位標準
- [Monitoring 03 SDK 設計](/monitoring/03-sdk-design/)：client-side SDK 埋點設計
- [Monitoring 06 商業方案](/monitoring/06-commercial-comparison/)：Sentry / Datadog RUM 的 client-side 能力比較
- [監控資料的雙重用途](/monitoring/telemetry-data-dual-use/)：同一份 event data 如何同時服務行為分析與訊號治理
