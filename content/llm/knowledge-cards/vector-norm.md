---
title: "Vector Norm"
date: 2026-05-12
description: "衡量向量大小的純量值、L1 / L2 / L∞ 各有用途、cosine similarity 的基礎"
weight: 1
tags: ["llm", "knowledge-cards", "math", "linear-algebra"]
---

Vector norm（向量範數）的核心概念是「**衡量向量「大小」的純量值**」。最常用的 L2 norm（歐式長度）= 把每個分量平方加總再開根號；但 L1、L∞ 等其他 norm 也在不同場景出現。Norm 在 LLM 中支撐 cosine similarity、layer normalization、gradient clipping 等核心機制，是 [vector database](/llm/knowledge-cards/vector-database/) 相似度搜尋的數學基礎。

## 概念位置

主流 norm 的定義與用途：

| Norm                | 定義              | LLM 中的用途                               |     |                                                        |
| ------------------- | ----------------- | ------------------------------------------ | --- | ------------------------------------------------------ |
| L1（Manhattan）     | `sum(             | v_i                                        | )`  | L1 regularization、稀疏化                              |
| **L2（Euclidean）** | `sqrt(sum(v_i²))` | 預設「向量長度」、cosine similarity 的分母 |     |                                                        |
| L∞（max）           | `max(             | v_i                                        | )`  | Gradient clipping by max value、某些 attention scaling |

L2 norm 在 LLM 中的關鍵應用：

1. **Cosine similarity**：`cos(a, b) = (a · b) / (||a||₂ × ||b||₂)`、衡量兩個向量的方向相似度、是 [RAG](/llm/knowledge-cards/rag/) / semantic search 的核心指標。
2. **[Embedding model](/llm/knowledge-cards/embedding-model/) 正規化**：通常把 embedding 正規化到 L2 norm = 1、之後 cosine similarity 退化成單純內積（[dot product](/llm/knowledge-cards/dot-product/)）、計算更快。
3. **Gradient clipping**：訓練時若 [gradient](/llm/knowledge-cards/gradient/) 的 L2 norm 超過閾值（如 1.0）、整體縮放回去、避免 [explosion](/llm/knowledge-cards/gradient-explosion-vanishing/)。
4. **[Layer normalization](/llm/knowledge-cards/layer-normalization/)**：RMSNorm 用 L2 norm（root mean square）做正規化。

## 設計責任

讀 RAG / embedding 教學看到「normalize embeddings」「cosine similarity」就是 L2 相關運算。寫 code 場景的判讀：用 [vector database](/llm/knowledge-cards/vector-database/) 時、若 embedding 已 L2-normalized、距離指標選 dot product 比 cosine 快（結果相同）；訓練 / fine-tune 自己 model 時、`gradient_clip: 1.0` 是常見預設、防止 gradient 偶發爆炸。
