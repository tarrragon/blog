---
title: "Constrained Decoding"
date: 2026-05-12
description: "推論時用 grammar 強制 LLM 輸出符合特定格式（JSON / regex / CFG）的 sampling 機制、把不合法 token 的機率歸零"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "structured-output"]
---

Constrained decoding（受限解碼）的核心概念是「**推論時用 grammar 動態算出每個位置的合法 token mask、把不合法 token 的 [logit](/llm/knowledge-cards/logit/) 設成 -∞、[softmax](/llm/knowledge-cards/softmax/) 後機率為 0**」。是 [structured output](/llm/04-applications/application-protocols/)（JSON mode / function calling 的合法性保證）背後的 sampling 機制。代表實作：XGrammar、outlines、lm-format-enforcer、guidance、SGLang。

## 跟其他概念的關係

跟既有 sampling 概念的層次：

```text
模型 forward pass → logits（每個 vocab token 一個分數）
   ↓ apply temperature
   ↓ apply grammar mask（constrained decoding）  ← 本卡聚焦
       - 算出當下位置的合法 token 集合
       - 不合法 token 的 logit 設 -∞
   ↓ softmax → 機率分佈
   ↓ sampling（greedy / top-p / top-k）
   ↓ next token
```

主要 [grammar](/llm/knowledge-cards/grammar/) 類型：

| Grammar 類型                | 描述                                | 用例                                   |
| --------------------------- | ----------------------------------- | -------------------------------------- |
| JSON Schema                 | 標準 JSON schema 定義合法 JSON 結構 | Function calling、structured output    |
| Regex                       | Regular expression                  | 受限文字格式（如 phone number、email） |
| CFG（Context-Free Grammar） | BNF 等 grammar 描述合法語法         | Code generation、DSL、SQL              |
| Choice list                 | 一組固定字串選項                    | Classification、enum 輸出              |

主流實作對比：

| 實作               | 機制                                         | 推論伺服器整合                    |
| ------------------ | -------------------------------------------- | --------------------------------- |
| **XGrammar**       | Pre-compile grammar → token mask cache、極快 | vLLM / SGLang / TensorRT-LLM 預設 |
| outlines           | Python lib、JSON schema / regex / CFG        | 用 Transformers / vLLM            |
| lm-format-enforcer | Lazy compile、適合動態 grammar               | Hugging Face Transformers         |
| guidance           | Microsoft 系、API 較高階                     | 自家 server                       |
| llama.cpp grammar  | Built-in GBNF（GGML BNF）                    | llama.cpp 內建                    |

## 判斷條件與後果

讀 sampling、structured output 或 function calling 的進階文件看到「constrained decoding」「grammar mask」「JSON schema enforcement」，指的就是這個機制。是否值得用，看輸出的下游怎麼使用它：

1. **下游 parser 容不下任何格式錯誤時**（function calling spec 嚴格、structured output 直接交給程式解析）：grammar mask 把不合法 token 的機率設成 0，輸出在語法上合法，省掉解析失敗之後的 retry。
2. **輸出是自由或創意文字時**：grammar 限制了模型能用的 token，也就限制了表達。grammar 寫得太嚴時，模型要表達的內容不在合法集合裡，只能選一個合法而錯誤的值，例如 enum 不含「unknown」時，模型被迫從現有選項挑一個。
3. **跟 function calling 的關係**：function calling 是「模型訓練 + structured output」，constrained decoding 是 sampling 層的工程實作，兩者可以獨立組合。
4. **生成速度**：XGrammar 這類 pre-compiled 實作在實測中反而**加速**生成，原因是 grammar 已經確定的 boilerplate token 不必由模型逐一生成，省下 forward pass。
5. **跟 [3.10 constrained decoding 章節](/llm/03-theoretical-foundations/constrained-decoding-internals/) 的關係**：本卡是定義、章節是內部機制（token mask 計算、CFG 編譯、性能取捨）
