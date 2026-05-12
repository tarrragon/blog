---
title: "Causal Mask"
date: 2026-05-12
description: "在 self-attention 裡擋掉「未來位置」的遮罩、讓 LLM 自回歸生成在訓練時也成立"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

Causal mask（因果遮罩）的核心概念是「在 [self-attention](/llm/knowledge-cards/self-attention/) 計算時、把 token i 看 token j (j > i) 的 attention 分數設成 -∞、[softmax](/llm/knowledge-cards/softmax/) 後機率為 0」。直覺：LLM 是 [autoregressive](/llm/knowledge-cards/autoregressive/) 的、生成 token N 時不能看到 N+1 以後（後面還沒生）、causal mask 強制這個約束、是 decoder-only Transformer 的標誌。

## 概念位置

Causal mask 在 attention 計算中的位置：

```text
score = Q @ K^T / sqrt(d)     ← shape (seq_len, seq_len)、每對 token 一個分數
score = score + causal_mask   ← 加上 mask
attention = softmax(score) @ V

causal_mask 長這樣（lower triangular、上三角全是 -∞）：
        K_0    K_1    K_2    K_3
Q_0   [  0    -∞     -∞     -∞ ]   ← token 0 只能看自己
Q_1   [  0     0     -∞     -∞ ]   ← token 1 能看 0~1
Q_2   [  0     0      0     -∞ ]
Q_3   [  0     0      0      0 ]
```

關鍵特性：

1. **訓練時並行有效**：所有 token 同時跑 forward pass、causal mask 確保每個 token 只看到該看的範圍。沒 mask 就會「偷看未來」、訓出 cheating 模型。
2. **推論時自動成立**：自回歸生成本來就是一個一個生、後面不存在、mask 是隱式的。
3. **跟 [KV cache](/llm/knowledge-cards/kv-cache/) 結合**：推論時 cache 只存「過去」的 K/V、causal mask 自然滿足。

跟其他 attention 變體的關係：

| 架構                                    | 是否用 causal mask               |
| --------------------------------------- | -------------------------------- |
| Decoder-only LLM（GPT / Llama / Gemma） | 用、是標配                       |
| Encoder-only（BERT）                    | 不用、可以看雙向 context         |
| Encoder-decoder（T5）                   | Decoder 部分用、Encoder 部分不用 |

## 設計責任

讀 paper / model card 看到「causal」「decoder-only」「auto-regressive」這幾組詞、就是這個機制。實務上、寫 code 場景的所有主流 LLM 都用 causal mask、所以這個概念是隱式 default、不會主動暴露給使用者；但理解它能解釋為什麼 LLM 是「接龍」、為什麼 [bidirectional context](/llm/knowledge-cards/context-window/) 在 LLM 裡不存在（要 bidirectional 要用 encoder 架構）。
