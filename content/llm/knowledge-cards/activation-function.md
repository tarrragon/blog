---
title: "Activation Function"
date: 2026-05-12
description: "在 linear layer 之間插入的非線性函數、讓神經網路能表達非線性關係"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "math"]
---

Activation function（激活函數）的核心概念是「在 linear layer（矩陣乘法）之間插入的非線性函數」。沒有 activation function、整個多層神經網路會塌縮成單一個線性變換、表達能力跟單層 linear 一樣弱。activation function 讓深度網路真的「深」起來。

## 概念位置

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

## 設計責任

讀 paper / model card 看到 SwiGLU、ReLU、GELU 等詞、知道它們是 FFN 內部的選擇、影響模型表達能力跟訓練穩定性、不影響「模型怎麼用 / 怎麼 inference」這類使用者面議題。寫 code 場景的判讀：模型用什麼 activation 由模型作者決定、使用者通常不用調；但若要 fine-tune 或自己訓模型、activation 選擇是設計決策之一。
