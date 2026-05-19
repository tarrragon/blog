---
title: "Sentry → Honeycomb：trace 不是 error、是不同 observability paradigm"
date: 2026-05-19
description: "Sentry → Honeycomb 是 paradigm shift — Sentry 主軸是 error tracking + transaction trace、Honeycomb 主軸是 high-cardinality wide-event observability；本文釐清 paradigm 邊界、5 個 production 踩雷（event schema 對位 / sampling 行為 / error grouping 失效 / cost 模型差 / alert paradigm shift）"
weight: 11
tags: ["backend", "observability", "sentry", "honeycomb", "paradigm-shift", "migration", "type-e"]
---

> 本文是跨 vendor migration playbook、cross-link [Sentry](/backend/04-observability/vendors/sentry/) 跟 [Honeycomb](/backend/04-observability/vendors/honeycomb/)。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Paradigm = High（error tracking ↔ wide-event observability）→ Type E paradigm shift*。

## Trace 不是 error、是不同 paradigm

把 Sentry → Honeycomb 當「trace tool 替換」是最常見的誤判 — Sentry trace 是 *error 上下文*、Honeycomb trace 是 *observability 第一性*：

| 概念          | Sentry                             | Honeycomb                                        |
| ------------- | ---------------------------------- | ------------------------------------------------ |
| 核心 paradigm | Error tracking + transaction trace | High-cardinality wide-event observability        |
| 第一性 unit   | Error event                        | Wide event (span with N fields)                  |
| Trace 角色    | Error 的「附帶 context」           | Observability 主軸、每 event 是 trace span       |
| Sampling      | Error 全收 + transaction sample    | Adaptive sampling、保留 *anomaly*                |
| Query model   | Filter + group by + aggregation    | High-cardinality 多維 query (BubbleUp / heatmap) |
| User base     | Developer (debug error)            | SRE + Platform (debug system behavior)           |
| Cost model    | Per-error event + transaction      | Per-event (wide event volume)                    |

**核心差異不在「Honeycomb 是 better Sentry」、在「兩者是不同 observability paradigm」**：

- Sentry 適合 *application-level error debug* — 拿到 error stack trace + minimal context、快速 fix
- Honeycomb 適合 *system-level behavior debug* — 看流量分佈 / 多維 correlation / 異常 outlier、找 *為什麼這個 user 在這個時段在這個 endpoint 慢*

**Migration scope 包含 *paradigm reset* — 不是 SDK 換、是 SRE / Dev team 對 observability 的心智模型重設**。

## 為什麼遷：observability 成熟度 / cardinality / cost 三條 driver

| Driver               | 觸發                                                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Observability 成熟度 | Application 規模到 *跨多 service / multi-tenant*、Sentry error tracking 不夠細、SRE 要看 *high-cardinality* 多維 query |
| High-cardinality     | Sentry tag system 限制 cardinality（~1000 unique value）、Honeycomb native 支援 millions cardinality                   |
| Cost                 | Per-error pricing 對 high-error volume 場景爆、Honeycomb per-event 在 *wide event* 場景更可預測                        |

反向 driver（Honeycomb → Sentry）：

- Pure error tracking 場景、Honeycomb wide-event 過度設計
- Frontend / mobile 客戶端 error tracking、Sentry 對 web/mobile/desktop SDK 成熟度高

## 6 維 audit

| 維度               | 等級                                                  |
| ------------------ | ----------------------------------------------------- |
| Schema / API       | Medium（event schema 概念不同、SDK 完全換）           |
| Operational        | Low（兩者都 SaaS、operational 對等）                  |
| Paradigm           | **High**（error tracking ↔ wide-event observability） |
| Components         | Low（同 1 個 observability vendor）                   |
| Application change | **High**（SDK 換 + instrumentation 重設計）           |
| Data topology      | Low                                                   |

Paradigm = High（其他 Low-Medium）→ Type E paradigm shift；application change 雖 High 但是 paradigm 的 downstream。

## 結構：partial migration + 混合架構是 long-term default

跟 [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) / [Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/) 同 Type E pattern：

- **不存在 complete migration**：Sentry 對 *frontend error tracking* 強項、Honeycomb 對 *backend system observability* 強項
- **長期混合架構**：frontend / mobile 保留 Sentry、backend / SRE 走 Honeycomb
- **Application 重設計**：instrumentation 用 OpenTelemetry、避免 vendor SDK lock-in

## Application 重設計範例

```python
# Before: Sentry SDK
import sentry_sdk
sentry_sdk.init(dsn='https://x@sentry.io/y')

try:
    process_order(order_id)
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise

# After: OpenTelemetry + Honeycomb
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint='https://api.honeycomb.io', headers={'x-honeycomb-team': 'YOUR_API_KEY'}))
)
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span('process_order') as span:
    span.set_attribute('order.id', order_id)
    span.set_attribute('user.id', user_id)
    span.set_attribute('order.amount', order.amount)  # high-cardinality 自然
    span.set_attribute('order.region', region)
    try:
        process_order(order_id)
        span.set_status(trace.Status(trace.StatusCode.OK))
    except Exception as e:
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        span.record_exception(e)
        raise
```

差異：

- Sentry 只 capture exception + 簡 context
- Honeycomb 對每 operation 寫 *wide event* 含 high-cardinality field（user.id / order.amount / order.region）
- SRE 端能跑 `WHERE order.region = "us-west-2" AND duration > 5000` 的 multi-dim query

## Migration 流程

```text
1. Audit application：列所有 Sentry SDK 使用 + capture pattern
2. 分類處理 plan:
   - Pure error tracking (frontend): 保留 Sentry
   - Backend system trace: 切 Honeycomb / OTel
   - Error + context (混合): 雙寫期 evaluate
3. OpenTelemetry instrumentation 化:
   - 用 OTel SDK 取代 vendor SDK
   - Honeycomb 是 OTLP target、跟 vendor lock 解耦
4. Backend application 切 Honeycomb (3-6 個月)
5. Frontend / mobile 保留 Sentry
6. SRE training: Honeycomb BubbleUp / heatmap / multi-dim query
```

## Production 故障演練

### Case 1：Event schema 對位失敗、SRE 不會用 BubbleUp

**徵兆**：切 Honeycomb 後 SRE 用 Sentry 思維 — 找 error → fix；Honeycomb BubbleUp / heatmap 沒人會用、observability 退化到 *只看 error count*。

**根因**：Sentry → Honeycomb migration 不只是 tool 換、是 *observability mindset 換*；SRE 沒培訓 wide-event query / BubbleUp anomaly detection。

**修法**：

1. **SRE training**：1-2 週 hands-on Honeycomb BubbleUp + heatmap + multi-dim query
2. **Migration scope 含 sample query playbook**：每個 incident type 對應 Honeycomb query 寫成 runbook
3. **保留 Sentry frontend / mobile**：不要逼 SRE 全切、保留 *paradigm fit* 的部分

### Case 2：Sampling 行為差、production cost 飛

**徵兆**：切 Honeycomb 後第 1 個月 event volume 比 Sentry 高 100x；帳單暴漲。

**根因**：Sentry 對 transaction 端 sample（10% 預設）、error 全收；Honeycomb 端 *每 span 都 wide event*、application 端沒設 sampling 全送、event volume 爆。

**修法**：

1. **Honeycomb Refinery (sampling proxy)**：deploy refinery 在 application 端跟 Honeycomb 之間、tail-based sampling
2. **Sample rule**：保留 *anomaly* (error / slow / outlier)、drop *boring success* 90%+
3. **Cost monitoring 第一週密集**：cardinality + event volume + cost dashboard、catch 預期外 spike

### Case 3：Error grouping 失效

**徵兆**：切 Honeycomb 後 *相似 error* 沒被 group 成「同類 issue」、SRE 看每 event 獨立、failure 模式淹沒在 noise。

**根因**：Sentry 自動 error grouping (by stack trace fingerprint)、Honeycomb 沒對等 — wide event 是 first-class、event grouping 需要 application 端 explicit 設 `error.type` field。

**修法**：

1. **Application 端設 error type field**：`span.set_attribute('error.type', exception_class)`
2. **Honeycomb derived column**：用 derived column 算 error fingerprint
3. **保留 Sentry error tracking**：純 error grouping 場景 Sentry 強項、別硬切

### Case 4：Cost 模型差、預估錯

**徵兆**：切 Honeycomb 後預估 50% cost saving、實際只省 10-15%。

**根因**：Sentry per-error pricing 對 error-heavy application 貴；Honeycomb per-event pricing 對 *wide event volume* application 貴；如果 application 是 *event volume 高 但 error 少*、Honeycomb 反而貴。

**修法**：

1. **Pre-migration 估**：用 OTel pilot 跑 1-2 週、估真實 event volume
2. **Sample rule 設計**：retention 7 天 hot + 30 天 cold + 1 年 archive、降 cost
3. **混合架構保留**：frontend / mobile 走 Sentry、backend 走 Honeycomb、避免一邊 cost 爆

### Case 5：Alert paradigm 不對等

**徵兆**：Sentry alert 簡單（error rate / latency p99 threshold）、Honeycomb trigger 配置複雜（SLO + burn rate + BubbleUp）；SOC 學習曲線 1-2 個月。

**修法**：

1. **Migration 含 alert rebuild scope**：Honeycomb trigger 不直接對位 Sentry alert、要重寫
2. **SLO-driven alert**：用 Honeycomb SLO 取代 Sentry threshold alert、降 alert fatigue
3. **PagerDuty integration**：兩家都支援、routing rule 跟 dedup 要 review

## Capacity / cost

| 維度                   | Sentry                        | Honeycomb                             |
| ---------------------- | ----------------------------- | ------------------------------------- |
| Pricing model          | Per-error + transaction       | Per-event (wide event)                |
| Cost (mid-tier)        | $500-2000 / mo                | $400-3000 / mo (依 event volume)      |
| Sampling               | Built-in transaction sampling | Refinery (additional component)       |
| Cardinality            | ~1000 unique value / tag      | Millions / field                      |
| Application complexity | Low (SDK + capture exception) | Medium (OTel + wide event instrument) |
| Migration cost         | -                             | 2-4 FTE × 2-3 個月                    |

## 整合 / 下一步

### 跟 OpenTelemetry 整合

OTel 是 vendor-neutral instrumentation、Honeycomb 是 OTLP backend；application 端 OTel 化後可以同時 ship 到多個 backend（dev 端 Jaeger / production 端 Honeycomb / fallback 端 Tempo）。

### 跟 [Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/) 對位

兩條 observability 路線：

- Grafana Stack (Mimir / Loki / Tempo)：self-host or Grafana Cloud、open source baseline
- Honeycomb：SaaS-only、focus wide-event observability

選擇取決於 *observability paradigm*：trace-heavy 走 Tempo / Honeycomb、metric-heavy 走 Mimir / Datadog。

## 相關連結

- Source vendor：[Sentry](/backend/04-observability/vendors/sentry/)
- Target vendor：[Honeycomb](/backend/04-observability/vendors/honeycomb/)
- 平行 migration playbook (Type E)：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) / [Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/) / [etcd → Consul](/backend/05-deployment-platform/vendors/consul/migrate-from-etcd/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
