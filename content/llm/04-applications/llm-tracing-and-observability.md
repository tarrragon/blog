---
title: "4.20 LLM tracing 與 observability"
date: 2026-05-12
description: "OpenTelemetry GenAI semantic conventions、結構化 span 設計、cost / latency 監控、failure debug 流程、跟 LLM-as-judge eval 的串接"
tags: ["llm", "applications", "observability", "tracing", "production", "opentelemetry"]
weight: 20
---

[LLM tracing](/llm/knowledge-cards/llm-tracing/) 把每次 LLM call / tool call / memory op / handoff 編成結構化 span、用 OpenTelemetry GenAI semantic conventions 標準化、是 production LLM 應用 debug / cost / quality 監控的事實標準。傳統 web app 的字串 logging 抓不到 LLM 應用的關鍵問題 — agent 為什麼選了那條路、reasoning trace 怎麼推導、tool call 為什麼 retry 三次、token 消耗為什麼比預期高 ×3。本章把 LLM tracing 的運作機制、OTel GenAI semconv、三大 use case（cost / latency / failure）跟 production eval 閉環拆成可操作的工程實務。

## 本章目標

讀完本章後、你應該能：

1. 解釋 LLM tracing 跟 traditional logging 的差異。
2. 用 OpenTelemetry GenAI semantic conventions 設計 span 結構。
3. 用 trace 做 cost / latency 監控跟 failure debug。
4. 把 production trace 餵回 [LLM-as-judge](/llm/04-applications/llm-as-judge/) 做品質迴路。
5. 對自己應用判斷該用 self-host vs SaaS observability platform。

## Traditional logging 為什麼不夠

LLM 應用的 debug 問題對傳統 logging 太抽象：

| 場景                              | Logging 看到       | 真正需要的資訊                                    |
| --------------------------------- | ------------------ | ------------------------------------------------- |
| Agent 為什麼選 tool A 不選 tool B | `tool=A` 一行      | 完整 reasoning trace + 當下 context + tool list   |
| Token cost 為什麼高               | `tokens=15234`     | Input / output / cached token 分項 + 每 turn 累積 |
| Why TTFT 5 秒                     | `ttft=5012ms`      | Prefill 跟 cache miss、prompt length、queue time  |
| Tool 為什麼 retry 三次            | `tool error retry` | 每次 error message + LLM 的判讀 + retry 策略      |
| Agent 為什麼 infinite loop        | 大量重複 log       | 每 iteration 的 context + 為什麼沒判 terminate    |

LLM tracing 用「結構化 span + parent-child 關係 + 標準化 attribute」直接編碼這些訊息。

## OpenTelemetry GenAI semantic conventions

OTel GenAI semconv 是 2024-2025 標準化中的 trace schema。核心概念：

```text
Trace（一次 user query 從進來到 response）
  ├── Span: gen_ai.agent.invocation（agent loop iteration 1）
  │     ├── Span: gen_ai.client.operation（LLM call 1）
  │     │     attrs: model, temperature, input_tokens, output_tokens, cache_read
  │     ├── Span: gen_ai.tool.execution（tool: read_file）
  │     │     attrs: tool_name, input, output, duration
  │     └── Span: gen_ai.memory.read（retrieval）
  │           attrs: query, top_k, similarity_scores
  ├── Span: gen_ai.agent.invocation（iteration 2）
  │     └── ...
  └── Span: gen_ai.agent.terminate
        attrs: reason, total_tokens, total_cost
```

主要 attribute 分類：

| 類別     | 屬性 prefix         | 典型內容                                      |
| -------- | ------------------- | --------------------------------------------- |
| Model    | `gen_ai.request.*`  | model, temperature, top_p, max_tokens, stream |
| Usage    | `gen_ai.usage.*`    | input_tokens, output_tokens, cached_tokens    |
| Response | `gen_ai.response.*` | finish_reason, id                             |
| Tool     | `gen_ai.tool.*`     | name, parameters, result                      |
| Memory   | `gen_ai.memory.*`   | operation, store, query, hits                 |
| Cost     | `gen_ai.cost.*`     | usd, currency（vendor-specific）              |

實作概要（Python 例）：

```python
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("gen_ai.client.operation") as span:
    span.set_attribute(SpanAttributes.LLM_MODEL_NAME, "claude-sonnet-4-6")
    span.set_attribute(SpanAttributes.LLM_TEMPERATURE, 0.7)

    response = llm_client.chat(messages=...)

    span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, response.usage.input_tokens)
    span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, response.usage.output_tokens)
    span.set_attribute("gen_ai.usage.cached_tokens", response.usage.cache_read_tokens or 0)
```

實務上多用 framework auto-instrumentation（LangChain / LlamaIndex / Anthropic SDK 都有 OTel integration）、不必手寫 span。

## Use case 1：Cost monitoring

Trace 是 LLM 應用 cost 監控的核心 — token usage attribute 內建、不必另外算。

實作模式：

```text
1. Trace 端記錄 input_tokens / output_tokens / cached_tokens
2. Observability 平台用「per-model pricing table」算出 USD
3. Aggregate by：
   - User（哪個 user 燒最多）
   - Endpoint（哪條 API path 最貴）
   - Feature（哪個 feature 最費 token）
   - Time（哪天 spike）
```

典型 dashboard 指標：

| 指標                       | 直覺                                                      |
| -------------------------- | --------------------------------------------------------- |
| Total cost / day           | 整體燒錢趨勢                                              |
| Cost per user              | 找 power user 或 abuse                                    |
| Cost per request           | 看單 request 平均 cost、設 alert                          |
| Cached / total token ratio | [Prompt cache](/llm/knowledge-cards/prompt-cache/) 命中率 |
| Output / input token ratio | 輸出膨脹率、看 generation length 合理性                   |

## Use case 2：Latency / failure debug

Trace 自然編碼 latency tree、能定位「哪個 span 卡」：

```text
User query → response total: 5.2s
├── Agent iteration 1: 4.8s
│   ├── LLM call (claude): 4.2s     ← 主要時間在這
│   │   - prefill: 3.8s             ← prefill 太久、看 prompt 是否需要 cache
│   │   - generation: 0.4s
│   ├── tool: read_file: 0.5s
│   └── memory: retrieval: 0.1s
└── Agent iteration 2: 0.4s
```

從這 trace 看出「90% 時間在 prefill、開 prompt cache 可以救」、不必猜。

Failure debug：

```text
User query → response: ERROR
├── Agent iteration 1: success
│   └── LLM call: tool_call(run_bash, cmd="rm -rf /")
├── Agent iteration 2: failure
│   └── tool: run_bash: REJECTED by permission system
└── Agent fallback: error response

從 trace 看：tool call 被 permission 擋下、不是 LLM 自己亂、而是 user query 觸發危險 tool call、permission 正確擋下。
```

對應 [6.2 tool use 權限模型](/llm/06-security/tool-use-permission-model/) 跟 [hands-on permission-boundary](/llm/01-local-llm-services/hands-on/permission-boundary/) 的判讀。

## Use case 3：Production trace → eval loop

Production trace 是 [LLM-as-judge](/llm/04-applications/llm-as-judge/) 的最佳資料來源：

```text
Production users
   ↓ 產生 trace
Trace storage（LangSmith / Phoenix / Langfuse）
   ↓ filter（e.g. user thumbs-down 的 trace）
   ↓ sample N 個
LLM-as-judge eval
   ↓ rubric scoring
找出系統性問題（哪類 query 品質差）
   ↓
改 system prompt / tool / agent loop
   ↓
A/B test on production traces
```

這是 [4.14 benchmarking](/llm/04-applications/benchmarking-and-evaluation/) 提的「in-house benchmark」的具體 implementation — production trace 是最真實的 benchmark dataset。

## 主流平台選型

| 平台                    | 類型                   | 強項                             | 適合場景                       |
| ----------------------- | ---------------------- | -------------------------------- | ------------------------------ |
| LangSmith               | SaaS（LangChain 系）   | Auto-instrumentation 強、UI 完整 | LangChain / LangGraph user     |
| Phoenix                 | OSS + SaaS（Arize 系） | OpenInference 標準、可 self-host | 想 self-host + OTel native     |
| Langfuse                | OSS + SaaS             | 開源強、cost 監控好              | Cost / eval 中心、可 self-host |
| Braintrust              | SaaS                   | Eval + tracing 一體              | 重 eval workflow 的 team       |
| Datadog APM             | SaaS                   | 跟 traditional APM 整合          | 已用 Datadog、想統一監控       |
| Logfire                 | SaaS（Pydantic）       | 簡潔、Python 為主                | Python 為主、輕量              |
| Self-host OTel + Jaeger | OSS                    | 完全 self-host、最便宜           | 隱私敏感、cost 敏感、技術強    |

判讀：

1. **個人 / 小流量**：SaaS 免費 tier（LangSmith / Langfuse / Phoenix）夠用
2. **隱私敏感（user data 不能離本機）**：Self-host（Langfuse / Phoenix self-hosted、或 OTel + Jaeger）
3. **已有 observability stack**：用 OTel + 現有 Datadog / Grafana、別再加一層
4. **重 eval**：Braintrust / Langfuse 的 eval feature 強

## 跟 [4.9 production resource](/llm/04-applications/production-resource-planning/) 的關係

4.5 寫 production resource 的 6 個 dimension（concurrency / latency / cost / storage / observability / reliability）、其中 observability 是 4.5 點到、本章展開。讀者讀完 4.5 知道「需要 observability」、本章補「具體怎麼做」。

## 設計失敗模式

1. **過度 instrument**：每個 internal function 都加 span、trace overhead 大、實際 production noise 多

**緩解**：聚焦 LLM-related 跟跨 service 邊界、internal logic 不必 trace

2. **PII / sensitive data 寫進 span attribute**：user prompt、API key、會被 SaaS 平台看到

**緩解**：Span attribute 過 PII filter、敏感資料 hash / masking、跟 [6.4 跨雲端邊界](/llm/06-security/cross-cloud-local-data-boundary/) 結合

3. **不 sample**：production 100% trace、storage / cost 爆

**緩解**：Production sample rate < 10%、error / outlier 100% capture

4. **沒設 trace 保留期**：trace 越累積越多、舊 trace 沒人看但仍付儲存

**緩解**：明確保留 policy（如 7-30 天 hot、之後 archive 或刪）

5. **Trace 不跟 metric 串**：trace 是 sample、metric 是 aggregate、debug 要兩個一起看

**緩解**：cost / latency 也輸出 metric（Prometheus 等）、trace 補 specific instance debug

## 何時不需要 tracing

1. **純 demo / 個人玩**：log 字串夠用
2. **單一 LLM call、無 agent loop**：簡單到 grep log 也能 debug
3. **隱私極敏感且不 self-host**：trace 內容流向 SaaS 是邊界、評估 risk
4. **每 request 都 trace 的 overhead > 收益**：超低 latency 場景看是否 worth it

## 何時過時 / 何時不過時

**不會過時的部分**：

- LLM tracing 跟 traditional logging 的根本差異
- 結構化 span + parent-child 關係的 framing
- Cost monitoring / latency debug / failure debug 三大 use case
- Trace → eval 的閉環概念
- 5 個設計失敗模式

**會變的部分**：

- OTel GenAI semconv 的具體 attribute 名稱（仍在 stabilizing）
- 主流 SaaS 平台（每年 1-2 個新進入者）
- Auto-instrumentation 的支援度（持續擴展）
- 跟具體 framework 的整合方式

## 下一章

下一章：[4.21 LLM-as-judge 評估方法](/llm/04-applications/llm-as-judge/)、把 production trace 變成系統性 eval 的閉環。
