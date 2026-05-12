---
title: "Reasoning Model"
date: 2026-05-12
description: "訓練成自然輸出長 reasoning trace 的 LLM 變體、o1 / DeepSeek-R1 / Claude thinking 為代表"
weight: 1
tags: ["llm", "knowledge-cards", "reasoning", "model-family"]
---

Reasoning model 的核心概念是「**透過後訓練（多半是 RL）讓模型自然在回答前產出長 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) reasoning trace 的 LLM 變體**」。代表是 OpenAI o1 / o3、DeepSeek-R1、Qwen-QwQ、Claude 3.7 Sonnet thinking 等。Reasoning model 是 2024-2026 LLM 的最大 paradigm shift、把 [test-time compute](/llm/knowledge-cards/test-time-compute/) 變成可訓練、可 scale 的維度。

## 概念位置

Reasoning model 跟一般 instruction-tuned model 的差異：

| 維度         | Instruction-tuned model（如 Gemma 4 instruct） | Reasoning model（如 DeepSeek-R1）            |
| ------------ | ---------------------------------------------- | -------------------------------------------- |
| 訓練後階段   | SFT + RLHF / DPO                               | SFT + RLHF + **reasoning RL**                |
| 推論行為     | 直接答（或短 CoT）                             | 先生 reasoning trace（數百到數千 token）再答 |
| 適合任務     | 對話、寫作、簡單 coding、查詢                  | math、debug、algorithm、複雜 reasoning       |
| Token 消耗   | 直接生答案 token                               | reasoning trace 通常 5-50× 於最終答案        |
| 推論成本     | 1×                                             | 5-20×（依任務難度）                          |
| Context 需求 | 一般                                           | 較大（要容納 reasoning trace）               |

主流 reasoning model 比較（2026/5）：

| 模型                       | 開源 / 商業 | 推理 trace 格式                  | 本地跑可行性                               |
| -------------------------- | ----------- | -------------------------------- | ------------------------------------------ |
| OpenAI o1 / o3             | 商業 API    | 對使用者隱藏                     | 不可                                       |
| DeepSeek-R1（full）        | 開源        | `<think>...</think>` 標記        | 671B 太大、本地不實際                      |
| DeepSeek-R1 distill        | 開源        | 同上                             | 7B / 14B / 32B distill 可在 24-48GB Mac 跑 |
| Qwen-QwQ                   | 開源        | 純文字 reasoning（無特殊 token） | 32B 可在 64GB+ Mac 跑                      |
| Claude 3.7 Sonnet thinking | 商業 API    | extended thinking field          | 不可                                       |
| Gemini 2.5 Flash thinking  | 商業 API    | thinking field                   | 不可                                       |

## 設計責任

讀 model card / paper 看到「reasoning」「thinking」「test-time compute」「R1-style」就是這個 family。寫 code 場景的判讀：

1. **本地用 distill 版本是合理起點**：DeepSeek-R1-Distill-Qwen-32B、QwQ-32B 等是「正常 32B 模型 + reasoning 後訓練」的產物、跑得起來
2. **適合的任務**：debug 複雜 bug、算 algorithm complexity、設計 multi-step refactor、解 leetcode hard
3. **不適合的任務**：autocomplete（reasoning trace 拉長 TTFT、體感變慢）、簡單 docstring 補完、純文字翻譯
4. **混用策略**：日常用 [instruction-tuned model](/llm/knowledge-cards/instruction-tuned/)（如 Gemma 4 31B、Qwen3-Coder）+ 複雜任務切到本地 reasoning model（如 QwQ-32B）+ 真正困難任務切雲端 o1 / R1 full
5. **記憶體預算**：reasoning model 本身大小跟對應 instruct model 相當、但要預留更大 [KV cache](/llm/knowledge-cards/kv-cache/) 給長 reasoning trace（context 通常開 32K+）
