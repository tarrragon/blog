---
title: "LLM Tracing"
date: 2026-05-12
description: "把 LLM 應用的每次 LLM call / tool call / memory op 編成結構化 span、用 OpenTelemetry GenAI semantic conventions 標準化"
weight: 1
tags: ["llm", "knowledge-cards", "observability", "production"]
---

LLM tracing 的核心概念是「**把 LLM 應用的每次 LLM call / tool call / memory op / handoff 編成結構化 span、串成 trace、可在 observability 平台查詢**」。對應的標準是 OpenTelemetry GenAI semantic conventions（2025 stabilizing 中）。代表平台：LangSmith、Phoenix、Braintrust、Langfuse、Datadog APM、Logfire。是 production LLM 應用 debug / cost / latency 監控的事實標準、補 traditional logging 抓不到的「為什麼 agent 跑這條路」。

## 概念位置

跟 traditional logging 的對比：

| 維度          | Traditional logging      | LLM tracing                                                            |
| ------------- | ------------------------ | ---------------------------------------------------------------------- |
| 結構          | 字串 line、靠 grep       | 結構化 span、parent-child 樹                                           |
| 關聯性        | 弱（要靠 request-id 串） | 強（trace-id + span 父子關係內建）                                     |
| 屬性          | 自由 key-value           | 標準化（OTel GenAI semconv）：model / temperature / token usage / cost |
| 查詢          | grep / log aggregator    | Trace explorer + filter + 視覺化                                       |
| LLM 特有 attr | 沒有                     | system prompt / tool calls / token / reasoning                         |

主流 OTel GenAI span 類型：

| Span 類型                  | 內容                      |
| -------------------------- | ------------------------- |
| `gen_ai.client.operation`  | 一次完整 LLM API call     |
| `gen_ai.tool.execution`    | 一次 tool 執行            |
| `gen_ai.agent`             | Agent loop 一個 iteration |
| `gen_ai.embeddings`        | Embedding call            |
| `gen_ai.memory.read/write` | Memory 操作               |

每個 span 標準屬性：`gen_ai.system`（vendor）、`gen_ai.request.model`、`gen_ai.usage.input_tokens` / `output_tokens`、`gen_ai.request.temperature` 等。

## 設計責任

讀 LLM observability docs / OTel spec 看到「span」「trace」「OTel GenAI semconv」就是這 framing。寫 code 場景的判讀：

1. **何時值得加 tracing**：超過個人 demo、有實際使用者 / production 流量、開始遇到「為什麼 agent 跑這條路」debug 問題
2. **不該自己寫 logging**：用 OTel GenAI semconv 標準化、未來可換 backend（LangSmith → Phoenix → 自架）
3. **Trace 不只 debug、也是 eval 來源**：production trace 餵回 [LLM-as-judge](/llm/knowledge-cards/llm-as-judge/) 做品質評估
4. **跟 [4.20 LLM tracing 章節](/llm/04-applications/llm-tracing-and-observability/) 的關係**：本卡是定義、章節是工程實務（attribute 設計、cost monitoring、failure debug 流程）
