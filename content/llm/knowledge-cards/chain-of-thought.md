---
title: "Chain-of-Thought（CoT）"
date: 2026-05-12
description: "讓 LLM 先輸出推理步驟再給最終答案的 prompting / 訓練方式、reasoning model 的基礎機制"
weight: 1
tags: ["llm", "knowledge-cards", "reasoning", "prompting"]
---

Chain-of-Thought（CoT、思維鏈、Wei et al., 2022）的核心概念是「**讓 LLM 先輸出一連串中間推理步驟、再給最終答案**」、不是直接從問題跳到結論。CoT 是 [reasoning model](/llm/knowledge-cards/reasoning-model/) 的基礎機制；prompting 形式（few-shot 提示）跟訓練形式（reasoning RLHF / RL）兩條路都圍繞它演化。

## 概念位置

CoT 的兩種觸發方式：

```text
直接回答：
  Q: 23 × 47 = ?
  A: 1081

Chain-of-Thought：
  Q: 23 × 47 = ?
  A: 先算 20 × 47 = 940、再算 3 × 47 = 141、加起來 940 + 141 = 1081。
     答案：1081
```

CoT 在 LLM 演化中的兩個階段：

| 階段          | 觸發方式                                                        | 代表模型 / 技術                                            |
| ------------- | --------------------------------------------------------------- | ---------------------------------------------------------- |
| Prompting CoT | Few-shot 提示「請逐步思考」或「let's think step by step」       | GPT-3、PaLM、早期 instruct 模型                            |
| Training CoT  | 訓練資料含大量 reasoning trace、模型學會「自然」用 CoT          | GPT-4、Claude 3.5、Gemini Pro                              |
| Reasoning RL  | RL 階段獎勵「正確答案的長 reasoning trace」、模型學會用更長 CoT | DeepSeek-R1、o1 / o3、Qwen-QwQ、Claude 3.7 Sonnet thinking |

第三階段的特性：模型自己決定「該想多久」（[test-time compute](/llm/knowledge-cards/test-time-compute/) 動態擴展）、推理 trace 可達數千 token、最終答案才是少數 token。

## 設計責任

讀 prompt engineering / paper 看到「CoT」「step by step」「reasoning trace」「thinking」等就是這個機制。寫 code 場景的判讀：

1. **複雜推理任務開 CoT 通常有幫助**（math、debug、algorithm design）— 即使是 instruct model 也能透過 prompting 觸發
2. **簡單任務 CoT 浪費 token**（autocomplete、單行查詢、純查表）
3. **Reasoning model 的 CoT 是內建行為**、不需要用 prompt 觸發、但 reasoning trace 會消耗大量 [token](/llm/knowledge-cards/token/)（推論時間、context、API 成本都翻倍）
4. **本地跑 reasoning model**：DeepSeek-R1 distill 系列、Qwen-QwQ 等可本地跑、但需要較大 [context window](/llm/knowledge-cards/context-window/) 容納 reasoning trace
