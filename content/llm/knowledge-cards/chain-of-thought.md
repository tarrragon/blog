---
title: "Chain-of-Thought（CoT）"
date: 2026-05-12
description: "讓 LLM 先輸出推理步驟再給最終答案的 prompting / 訓練方式、reasoning model 的基礎機制"
weight: 1
tags: ["llm", "knowledge-cards", "reasoning", "prompting"]
---

Chain-of-Thought（CoT、思維鏈、Wei et al., 2022）的核心概念是「**讓 LLM 先輸出一連串中間推理步驟、再給最終答案**」、不是直接從問題跳到結論。CoT 是 [reasoning model](/llm/knowledge-cards/reasoning-model/) 的基礎機制；prompting 形式（few-shot 提示）跟訓練形式（reasoning RLHF / RL）兩條路都圍繞它演化。

## 跟其他概念的關係

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

## 判斷條件與後果

讀 prompt engineering 文章或 paper 看到「CoT」「step by step」「reasoning trace」「thinking」，指的就是這個機制。CoT 帶來的是品質還是浪費，看任務的答案是否依賴中間步驟：

- **多步推理的任務**（math、debug、algorithm design）：模型先寫出的中間步驟會成為後面 token 的輸入，最終答案能依據已經算好的部分結果，所以開 CoT 通常有幫助，instruct model 用 prompting 也觸發得了。
- **單步任務**（autocomplete、單行查詢、純查表）：答案不依賴中間步驟，CoT 多產生的 token 只增加延遲與成本。
- **Reasoning model**：CoT 是內建行為，不需要 prompt 觸發，但 reasoning trace 會消耗大量 [token](/llm/knowledge-cards/token/)，推論時間、context 用量與 API 成本都隨 trace 長度增加。本地跑 DeepSeek-R1 distill、Qwen-QwQ 這類模型時，[context window](/llm/knowledge-cards/context-window/) 要留得下 trace，留不下時 trace 會被截斷。
