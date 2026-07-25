---
title: "Logit"
date: 2026-05-12
description: "softmax 之前的原始實數分數、每個 vocab token 一個值、可正可負"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "math"]
---

Logit 的核心概念是「[softmax](/llm/knowledge-cards/softmax/) 之前的原始分數」。LLM 每次 forward pass 的最後一步、會輸出長度為 vocab size 的實數向量（例如 vocab size = 128K、輸出就是 128K 個浮點數）、這個向量就是 logits。Logit 可正可負、無上下界、要經過 softmax 才變成機率分佈。

## 概念位置

Logit 在 LLM 輸出 pipeline 的位置：

```text
最後一層 Transformer 輸出 hidden state
   ↓ output projection（linear layer）
logits（shape: vocab_size、實數、可正可負）
   ↓ logit warping / masking（可選、用於控制輸出）
   ↓ /temperature
   ↓ softmax
probability distribution
   ↓ sampling（greedy / top-k / top-p）
next token
```

操作 logit 的常見技巧：

| 技巧               | 做法                                 | 用途                                                                               |
| ------------------ | ------------------------------------ | ---------------------------------------------------------------------------------- |
| Temperature        | logit / T                            | 控制輸出隨機度、T 越大越平                                                         |
| Logit bias         | 對特定 token 的 logit 加 / 減 offset | 強制 / 抑制特定 token（如禁用特定詞）                                              |
| Grammar masking    | 把不合法 token 的 logit 設成 -∞      | [Structured output](/llm/knowledge-cards/structured-output/)、確保輸出符合 grammar |
| Repetition penalty | 對最近出現過的 token logit 扣分      | 避免重複、改善生成多樣性                                                           |

## 設計責任

理解 logit 後可以判讀 sampling 階段的控制粒度：所有「不重訓模型、影響輸出」的技巧（temperature、structured output、constrained generation、logit bias）本質上都是「在 softmax 前後動 logit」、不是動模型權重。這也是為什麼同一個模型用不同 sampling 設定能產生差很多的輸出。
