---
title: "Activation Function"
date: 2026-05-12
description: "在 linear layer 之間插入的非線性函數、讓神經網路能表達非線性關係"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "math"]
---

Activation function（激活函數）的核心概念是「在 linear layer（[矩陣乘法](/llm/knowledge-cards/matrix-multiplication/)）之間插入的非線性函數」。沒有 activation function、整個多層神經網路會塌縮成單一個線性變換、表達能力跟單層 linear 一樣弱。activation function 讓深度網路真的「深」起來。

## 跟其他概念的關係

LLM 中 activation function 主要出現在 [FFN](/llm/knowledge-cards/ffn/) 內、夾在兩個矩陣乘法之間：

```text
FFN: input → W_up (linear) → activation → W_down (linear) → output
                              ↑
                       這裡是 activation function
```

主流 LLM 用的 activation function 演化：

| Activation | 公式（簡化）                    | 出現在                      |
| ---------- | ------------------------------- | --------------------------- |
| ReLU       | `max(0, x)`                     | 早期 Transformer（如 BERT） |
| GELU       | `x · Φ(x)`（Φ 是 Gaussian CDF） | GPT-2 / 3、BERT 後期        |
| SwiGLU     | `Swish(xW) ⊙ (xV)`              | Llama、Gemma、Qwen 等主流   |
| GeGLU      | `GELU(xW) ⊙ (xV)`               | 部分 Google 系列模型        |

SwiGLU / GeGLU 是「gated」變體、用兩條線性投影相乘、表達能力比單一 activation 強、是現代 LLM 主流。

## 判斷條件與後果

paper 或 model card 上的 SwiGLU、ReLU、GELU 是 FFN 內部的選擇，由模型作者在訓練之前決定，影響的是模型的表達能力與訓練穩定性。只是使用模型、做 inference 時，activation 已經固定在模型裡，部署方式與呼叫方式都不因它而不同，這些詞只用來辨認模型屬於哪一代的設計。自己訓練模型時，activation 是一個設計決策：gated 變體（SwiGLU、GeGLU）用兩條線性投影相乘，表達能力較強，代價是 FFN 多一組權重與對應的計算。fine-tune 時沿用原模型的 activation，原因是預訓練權重是配合那個函數學出來的。
