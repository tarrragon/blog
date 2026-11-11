---
title: "LLM Tracing"
date: 2026-05-12
description: "把 LLM 應用的每次 LLM call / tool call / memory op 編成結構化 span、用 OpenTelemetry GenAI semantic conventions 標準化"
weight: 1
tags: ["llm", "knowledge-cards", "observability", "production"]
---

LLM tracing 的核心概念是「**把 LLM 應用的每次 LLM call / [tool call](/llm/knowledge-cards/tool-use/) / memory op / handoff 編成結構化 span、串成 trace、可在 observability 平台查詢**」。對應的標準是 OpenTelemetry GenAI semantic conventions（2025 stabilizing 中）。代表平台：LangSmith、Phoenix、Braintrust、Langfuse、Datadog APM、Logfire。是 production LLM 應用 debug / cost / latency 監控的事實標準、補 traditional logging 抓不到的「為什麼 agent 跑這條路」。

## 跟其他概念的關係

跟 traditional logging 的對比：

| 維度          | Traditional logging      | LLM tracing                                                            |
| ------------- | ------------------------ | ---------------------------------------------------------------------- |
| 結構          | 字串 line、靠 grep       | 結構化 span、parent-child 樹                                           |
| 關聯性        | 弱（要靠 request-id 串） | 強（trace-id + span 父子關係內建）                                     |
| 屬性          | 自由 key-value           | 標準化（OTel GenAI semconv）：model / temperature / token usage / cost |
| 查詢          | grep / log aggregator    | Trace explorer + filter + 視覺化                                       |
| LLM 特有 attr | 沒有                     | system prompt / tool calls / token / reasoning                         |

主流 OTel GenAI span 類型：

| Span 類型                  | 內容                                                     |
| -------------------------- | -------------------------------------------------------- |
| `gen_ai.client.operation`  | 一次完整 LLM API call                                    |
| `gen_ai.tool.execution`    | 一次 tool 執行                                           |
| `gen_ai.agent`             | [Agent](/llm/knowledge-cards/agent/) loop 一個 iteration |
| `gen_ai.embeddings`        | Embedding call                                           |
| `gen_ai.memory.read/write` | Memory 操作                                              |

每個 span 標準屬性：`gen_ai.system`（vendor）、`gen_ai.request.model`、`gen_ai.usage.input_tokens` / `output_tokens`、`gen_ai.request.temperature` 等。

## 判斷條件與後果

tracing 是否值得加，看應用是否已經有個人 demo 以外的使用者與 production 流量。只有自己跑 demo 時，出錯的那一次自己重跑就看得到；有實際使用者之後，agent 在某一次請求裡為什麼走了那條路（呼叫了哪些 tool、讀了哪些 memory）重現不出來，只有當時記下的 span 樹查得到。

紀錄的格式決定之後是否能換平台：用自訂欄位寫 logging 時，紀錄綁在自己的欄位名稱上，換 observability 平台就要改寫記錄的程式；照 OTel GenAI semconv 的標準屬性記錄，同一份 trace 可以送到 LangSmith、Phoenix 或自架的 backend。trace 留下的 production 輸入與輸出同時是評估資料，餵給 [LLM-as-judge](/llm/knowledge-cards/llm-as-judge/) 定期評分時，品質回歸在真實流量上就會被抓到。attribute 設計、cost monitoring 與 failure debug 流程在 [4.20 LLM tracing 章節](/llm/04-applications/llm-tracing-and-observability/)。
