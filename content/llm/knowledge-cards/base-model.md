---
title: "Base Model"
date: 2026-05-11
description: "未經指令微調的原始模型：擅長文字接龍、適合下游微調用途"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Base Model 的核心概念是「LLM 訓練 pipeline 第一階段的產物」，只用大量文字做 next-token prediction、尚未做 [instruction tuning](/llm/knowledge-cards/instruction-tuned/) 或 RLHF。Base model 擅長「順著前面的文字接下去」，但對「使用者提問、模型回答」這種交互模式比較生硬。

## 概念位置

Base model 跟 instruction-tuned model 共用底層權重結構、差別在後續微調階段。對寫 code 場景的多數使用者來說、預設選 instruction-tuned 版本；base model 主要服務想自己微調的研究人員與工程師。

## 可觀察訊號與例子

Hugging Face / Ollama 上 base model 通常會明示：

| 名稱範例                 | 是 base model 嗎                                                      |
| ------------------------ | --------------------------------------------------------------------- |
| `llama-3.3-70b-base`     | 是                                                                    |
| `llama-3.3-70b-instruct` | 否（[已 instruction-tuned](/llm/knowledge-cards/instruction-tuned/)） |
| `gemma-3-27b`            | 視 repo 而定、要看 model card                                         |
| `qwen3-coder-30b`        | 否（coding-tuned 是 instruction-tuned 的特化）                        |

對話 base model 的體感：問「寫一個 Python fibonacci」可能得到「寫一個 Python fibonacci。寫一個 JavaScript fibonacci。寫一個...」這種文字接龍式回答、而非真正寫出 function。

## 設計責任

下載模型前確認是 instruct 還是 base 版本。Ollama registry 預設提供 instruct 版本、但 Hugging Face 上同一個模型常同時有兩種；挑錯版本會以為「這個模型很差」、其實只是用錯類型。想做 fine-tuning 的工程師才需要 base model；其他人優先選 instruct。
