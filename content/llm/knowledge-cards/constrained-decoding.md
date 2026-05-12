---
title: "Constrained Decoding"
date: 2026-05-12
description: "推論時用 grammar 強制 LLM 輸出符合特定格式（JSON / regex / CFG）的 sampling 機制、把不合法 token 的機率歸零"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "structured-output"]
---

Constrained decoding（受限解碼）的核心概念是「**推論時用 grammar 動態算出每個位置的合法 token mask、把不合法 token 的 [logit](/llm/knowledge-cards/logit/) 設成 -∞、[softmax](/llm/knowledge-cards/softmax/) 後機率為 0**」。是 [structured output](/llm/04-applications/application-protocols/)（JSON mode / function calling 的合法性保證）背後的 sampling 機制。代表實作：XGrammar、outlines、lm-format-enforcer、guidance、SGLang。

## 概念位置

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

主要 grammar 類型：

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

## 設計責任

讀 sampling / structured output / function calling 進階文件看到「constrained decoding」「grammar mask」「JSON schema enforcement」就是這 framing。寫 code 場景的判讀：

1. **何時值得用**：需要 100% 合法 JSON / 特定格式、function calling spec 嚴格、structured output 不可有解析錯誤
2. **不該用的情況**：自由 / 創意輸出（會限制模型表達）、grammar 太嚴讓模型「該說的話說不出來」（如 enum 不含「unknown」、模型強制選錯）
3. **跟 function calling 的關係**：function calling 是「模型訓練 + structured output」、constrained decoding 是 sampling 層的工程實作、可獨立組合
4. **加速 vs 拖慢**：常見誤解是 grammar 拖慢 — 實測 XGrammar 等 pre-compiled 實作反而**加速**生成（跳過 boilerplate token 直接生關鍵 token、節省 forward pass）
5. **跟 [3.10 constrained decoding 章節](/llm/03-theoretical-foundations/constrained-decoding-internals/) 的關係**：本卡是定義、章節是內部機制（token mask 計算、CFG 編譯、性能取捨）
