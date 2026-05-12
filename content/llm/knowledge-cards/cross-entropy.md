---
title: "Cross-Entropy"
date: 2026-05-12
description: "衡量「預測機率分佈」跟「真實分佈」距離的指標、LLM 預訓練的主要 loss"
weight: 1
tags: ["llm", "knowledge-cards", "training", "math"]
---

Cross-entropy（交叉熵）的核心概念是「衡量兩個機率分佈的距離」。LLM 預訓練的標準 [loss function](/llm/knowledge-cards/loss-function/) 是 cross-entropy：對每個 token、把模型預測的 vocab 機率分佈跟「真實答案是 one-hot 分佈」做 cross-entropy、加總。

## 概念位置

Cross-entropy 在 next-token prediction 訓練裡的具體計算：

```text
模型預測：p = softmax(logits)  ← shape: (vocab_size,)
真實答案：y = one-hot(true_token)  ← shape: (vocab_size,)、只有真實 token 那位是 1

cross-entropy = -sum(y_i × log(p_i))
              = -log(p_true_token)  ← 因為 y 是 one-hot、只剩這項
```

所以實作上 cross-entropy 就退化成「真實 token 預測機率的負對數」、機率越接近 1、loss 越接近 0；機率越接近 0、loss 越接近 ∞。

跟相關概念的關係：

| 概念                                                 | 跟 cross-entropy 的關係                                                                                              |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| [Perplexity](/llm/knowledge-cards/perplexity/)       | `perplexity = exp(cross-entropy)`、cross-entropy 的指數形式、人類直覺較好讀                                          |
| [KL divergence](/llm/knowledge-cards/kl-divergence/) | Cross-entropy = entropy(真實) + KL(真實 ‖ 預測)、訓練時 entropy 是常數、所以 minimize cross-entropy 等於 minimize KL |
| [Softmax](/llm/knowledge-cards/softmax/)             | Cross-entropy 通常吃 softmax 的輸出當「預測機率」                                                                    |

## 設計責任

讀 LLM 訓練 / paper 時看到「training loss」幾乎都是 cross-entropy。實務判讀：cross-entropy 直接代表「模型對真實 token 的預測機率有多差」、loss = 2 大致對應「真實 token 被預測機率 ≈ 0.135」（exp(-2)）。模型在 pretrain 階段 cross-entropy 從約 11（純隨機）降到約 2-3（成熟模型）、SFT 階段再略降。
