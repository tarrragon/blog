---
title: "Softmax"
date: 2026-05-12
description: "把任意實數向量正規化成「總和為 1、每個分量 ∈ [0,1]」的機率分佈"
weight: 1
tags: ["llm", "knowledge-cards", "math", "sampling"]
---

Softmax 的核心概念是「把一串實數轉成機率分佈」。公式是 `softmax(x_i) = exp(x_i) / sum(exp(x_j))`、輸出總和為 1、每個值 ∈ [0, 1]。它是 LLM 兩個關鍵環節的常駐元件：[attention](/llm/knowledge-cards/attention/) 的權重計算、跟 sampling 階段把 [logit](/llm/knowledge-cards/logit/) 轉成「下個 token 的機率分佈」。

## 概念位置

LLM 中 softmax 出現的兩個位置：

```text
位置 1：Attention 內部
  Q · K^T → 一堆 score
  softmax(scores) → attention weight（總和 1）
  weight · V → output

位置 2：每次 token 生成的最後一步
  最後一層 hidden → logit（每個 vocab token 一個實數分數）
  softmax(logits / temperature) → 機率分佈
  從這個分佈 sample 出下一個 token
```

兩個位置的關鍵差異：

| 位置        | softmax 的作用                               | 影響                          |
| ----------- | -------------------------------------------- | ----------------------------- |
| Attention   | 把 attention score 正規化成「該關注多少」    | 影響模型怎麼整合 context 資訊 |
| Sampling 端 | 把 logit 變機率、配合 temperature 調分佈陡度 | 影響輸出的多樣性 / 確定性     |

Temperature 在 sampling 端跟 softmax 結合：`softmax(logits / T)`、T 越小分佈越尖（接近 greedy）、T 越大分佈越平（接近隨機）。

## 設計責任

理解 softmax 後可以判讀幾件事：temperature 為什麼影響輸出多樣性（改的是 softmax 前的縮放）、為什麼 [logit](/llm/knowledge-cards/logit/) bias / logit warping 等技巧能控制輸出（直接動 softmax 的輸入）、為什麼 [structured output](/llm/04-applications/tool-use-principles/) 的 grammar-constrained sampling 是「把不合法 token 的機率歸零」（在 softmax 後或前做 masking）。
