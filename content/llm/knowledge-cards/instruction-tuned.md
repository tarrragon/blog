---
title: "Instruction-Tuned Model"
date: 2026-05-11
description: "經過指令微調的模型：會跟著 prompt 走、回答使用者問題"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Instruction-Tuned Model 的核心概念是「在 [base model](/llm/knowledge-cards/base-model/) 之上、用指令-回答對資料進一步微調」。微調目的是讓模型理解「使用者問 X、應該回答 Y」這種交互模式。寫 code 場景該用的就是 instruction-tuned 模型（多半標 `-instruct` 或 `-it`）。

## 概念位置

Instruction tuning 是 LLM 訓練 pipeline 的中間階段：base model（純文字接龍）→ instruction-tuned（會跟指令走）→ [RLHF](/llm/knowledge-cards/rlhf/)（進一步對齊人類偏好）。寫 code 用的 Gemma 4 31B、Qwen3-Coder 30B、Llama 3.3 70B 等都是 instruction-tuned 版本。

## 可觀察訊號與例子

Ollama tag 中的 `instruct`、`it` 是 instruction-tuned 標記：

| 模型 tag                       | 解讀                                         |
| ------------------------------ | -------------------------------------------- |
| `gemma4:31b-instruct-q5_K_M`   | Gemma 4、instruct-tuned                      |
| `llama3.3:70b-instruct-q4_K_M` | Llama 3.3、instruct-tuned                    |
| `qwen3-coder:30b`              | Qwen3-Coder（預設就是 instruct，未必額外標） |

Coding-tuned 是 instruction-tuned 的特化版本，再加上大量 code 訓練資料；Qwen3-Coder、Gemma 4 coding 版本都屬於這類。

## 設計責任

寫 code 場景的預設選擇是 instruction-tuned + coding-specialized 模型。看到 Ollama tag 沒有 `instruct` 字樣（如 `llama3.3:70b-base`）的版本、那是 [base model](/llm/knowledge-cards/base-model/)、跟指令走的能力較差、適合下游微調而非直接對話。
