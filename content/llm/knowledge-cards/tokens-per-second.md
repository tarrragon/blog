---
title: "Tokens Per Second"
date: 2026-05-11
description: "LLM 每秒能生成幾個 token：生字速度的標準量化指標"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Tokens Per Second（tok/s）的核心概念是「LLM 每秒能輸出多少個 [token](/llm/knowledge-cards/token/)」，是生字速度的標準指標。生字速度由 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 跟模型大小共同決定，而非 CPU / GPU 算力。

## 概念位置

Tok/s 量度的是 [autoregressive](/llm/knowledge-cards/autoregressive/) 主要生成階段的吞吐量，跟 [TTFT](/llm/knowledge-cards/ttft/)（首字延遲）是兩個獨立指標。一個系統可能 TTFT 高但 tok/s 還行，也可能 TTFT 低但 tok/s 慢；兩者都要看才能完整描述體感。

## 可觀察訊號與例子

實務經驗值（僅供量級參考、視硬體與量化等級而定）：

| 場景                     | 大致 tok/s |
| ------------------------ | ---------- |
| Claude Sonnet 雲端       | 80 ~ 120   |
| GPT-5 雲端               | 70 ~ 100   |
| Gemma 4 31B MTP / M4 Max | 25 ~ 40    |
| Qwen3-Coder 30B / M2 Pro | 15 ~ 25    |

體感分界：低於 10 tok/s 像 dial-up 般卡頓、20 tok/s 以上接近流暢閱讀速度、40 tok/s 以上感覺即時。

## 設計責任

評估本地 LLM 是否堪用時，tok/s 是核心指標之一。理論上限可用「[memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) ÷ 模型大小」估算，實際值會比理論低 30 ~ 50%。看到「N tok/s」的報告時要追問模型、[量化](/llm/knowledge-cards/quantization/) 等級、硬體，三者缺一個就無法比較。
