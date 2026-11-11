---
title: "Reasoning Model"
date: 2026-05-12
description: "訓練成自然輸出長 reasoning trace 的 LLM 變體、o1 / DeepSeek-R1 / Claude thinking 為代表"
weight: 1
tags: ["llm", "knowledge-cards", "reasoning", "model-family"]
---

Reasoning model 的核心概念是「**透過後訓練（多半是 RL）讓模型自然在回答前產出長 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) reasoning trace 的 LLM 變體**」。代表是 OpenAI o1 / o3、DeepSeek-R1、Qwen-QwQ、Claude 3.7 Sonnet thinking 等。Reasoning model 是 2024-2026 LLM 的最大 paradigm shift、把 [test-time compute](/llm/knowledge-cards/test-time-compute/) 變成可訓練、可 scale 的維度。

## 跟其他概念的關係

Reasoning model 跟一般 instruction-tuned model 的差異：

| 維度         | [Instruction-tuned model](/llm/knowledge-cards/instruction-tuned/)（如 Gemma 4 instruct） | Reasoning model（如 DeepSeek-R1）            |
| ------------ | ----------------------------------------------------------------------------------------- | -------------------------------------------- |
| 訓練後階段   | SFT + RLHF / DPO                                                                          | SFT + RLHF + **reasoning RL**                |
| 推論行為     | 直接答（或短 CoT）                                                                        | 先生 reasoning trace（數百到數千 token）再答 |
| 適合任務     | 對話、寫作、簡單 coding、查詢                                                             | math、debug、algorithm、複雜 reasoning       |
| Token 消耗   | 直接生答案 token                                                                          | reasoning trace 通常 5-50× 於最終答案        |
| 推論成本     | 1×                                                                                        | 5-20×（依任務難度）                          |
| Context 需求 | 一般                                                                                      | 較大（要容納 reasoning trace）               |

主流 reasoning model 比較（2026/5）：

| 模型                       | 開源 / 商業 | 推理 trace 格式                  | 本地跑可行性                               |
| -------------------------- | ----------- | -------------------------------- | ------------------------------------------ |
| OpenAI o1 / o3             | 商業 API    | 對使用者隱藏                     | 不可                                       |
| DeepSeek-R1（full）        | 開源        | `<think>...</think>` 標記        | 671B 太大、本地不實際                      |
| DeepSeek-R1 distill        | 開源        | 同上                             | 7B / 14B / 32B distill 可在 24-48GB Mac 跑 |
| Qwen-QwQ                   | 開源        | 純文字 reasoning（無特殊 token） | 32B 可在 64GB+ Mac 跑                      |
| Claude 3.7 Sonnet thinking | 商業 API    | extended thinking field          | 不可                                       |
| Gemini 2.5 Flash thinking  | 商業 API    | thinking field                   | 不可                                       |

## 判斷條件與後果

Reasoning model 每次作答前先產出數百到數千 token 的 reasoning trace（model card 寫「reasoning」「thinking」「R1-style」指的就是這類模型），這段 trace 同時帶來它的強項與成本，所以任務怎麼分配，看任務是否需要多步推導、使用者能否等待較長的回應時間：

- **任務需要多步推導時**（debug 複雜的 bug、算 algorithm complexity、設計 multi-step refactor、解 leetcode hard），trace 讓模型逐步推導再作答，答對率的提升抵得過 5–20 倍的推論成本。
- **任務要求即時回應、或本身不需要推導時**（autocomplete、簡單的 docstring 補完、純文字翻譯），trace 拉長 TTFT，使用者等得更久，答案卻不會更好。
- **兩類任務混在同一個工作流裡時**，日常任務交給 [instruction-tuned model](/llm/knowledge-cards/instruction-tuned/)（如 Gemma 4 31B、Qwen3-Coder），複雜任務切到本地的 reasoning model（如 QwQ-32B），本地模型做不出來的再交給雲端的 o1 或 R1 full，推論成本只花在需要推導的任務上。
- **在本地跑時**，DeepSeek-R1-Distill-Qwen-32B、QwQ-32B 這類 distill 版本是一般的 32B 模型加上 reasoning 後訓練，權重大小跟同級的 instruct 模型相當，24–48GB 的 Mac 放得下；多出來的記憶體需求在長 trace 佔用的 [KV cache](/llm/knowledge-cards/kv-cache/)，context 通常開到 32K 以上，記憶體預算要把這份 KV cache 算進去。
