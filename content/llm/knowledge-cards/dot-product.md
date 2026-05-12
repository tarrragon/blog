---
title: "Dot Product"
date: 2026-05-12
description: "兩個向量對應位置相乘再加總、attention score 跟相似度判讀的基礎"
weight: 1
tags: ["llm", "knowledge-cards", "math", "linear-algebra"]
---

Dot product（內積、inner product）的核心概念是「**兩個向量對應位置相乘再加總**」：`a · b = a₁b₁ + a₂b₂ + ... + aₙbₙ`。幾何意義是「a 在 b 方向上的投影長度 × b 的長度」。Dot product 是 LLM 中**最頻繁出現的運算之一**：[attention](/llm/knowledge-cards/attention/) 的核心是 dot product、cosine similarity 的本體也是 dot product。

## 概念位置

Dot product 在 LLM 中的核心應用：

| 應用                     | 公式 / 機制                                                     | 角色                                 |     |     |     |     |     |     |     |                                                    |
| ------------------------ | --------------------------------------------------------------- | ------------------------------------ | --- | --- | --- | --- | --- | --- | --- | -------------------------------------------------- |
| Attention score          | `Q · K^T`                                                       | 算「該 token 跟其他 token 的相關性」 |     |     |     |     |     |     |     |                                                    |
| Cosine similarity        | `(a · b) / (                                                    |                                      | a   |     | ₂ × |     | b   |     | ₂)` | [RAG](/llm/knowledge-cards/rag/) / semantic search |
| L2-normalized similarity | normalize 後直接用 `a · b`                                      | Vector database 高效檢索             |     |     |     |     |     |     |     |                                                    |
| Logits → token 機率      | output_projection 本質是「最後 hidden state · token embedding」 | 算每個 vocab token 的「匹配度」      |     |     |     |     |     |     |     |                                                    |

幾何直覺：

```text
兩個向量方向接近時：dot product 大（正值大）
兩個向量垂直時：    dot product = 0
兩個向量方向相反時：dot product 大負值

a · b = |a| × |b| × cos(θ)
                          ↑
                  θ 是兩向量夾角
```

LLM 推論性能上、dot product 是「[matrix multiplication](/llm/knowledge-cards/matrix-multiplication/) 的基本單元」、整個 forward pass 可以看成大量 dot product 的批次運算；這是為什麼 GPU / Apple Silicon Neural Engine 都針對 dot product 做硬體優化。

## 設計責任

讀 attention / RAG 相關內容看到「inner product」「dot product」「QK^T」就是這個運算。寫 code 場景的判讀：用 vector database 時、選 distance metric 看：cosine 適合未 normalized 的 embedding、dot product 適合 L2-normalized 的 embedding（兩者結果同、後者較快）；attention 的 KV cache 量化（K=Q8 / V=Q4）對品質的不對稱影響、根本原因是 K 用於 dot product（誤差累積快）、V 用於加權平均（誤差被平均化）。
