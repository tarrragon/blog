---
title: "Embedding Layer"
date: 2026-05-12
description: "Transformer 第一層的查表結構、把整數 token ID 轉成可運算的向量"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

Embedding layer（嵌入層）的核心概念是「Transformer 第一層的查表結構：把整數 [token](/llm/knowledge-cards/token/) ID 對應到一個可訓練向量（embedding）」。本質上是 `vocab_size × hidden_dim` 的權重矩陣、每個 token ID 取對應 row 當該 token 的向量表示。後續所有 Transformer block 都對這些向量做運算。

## 概念位置

Embedding layer 在 [forward pass](/llm/knowledge-cards/forward-pass/) 的位置：

```text
input："Hello world"
   ↓ tokenizer
token IDs: [9906, 1917]            ← 整數序列
   ↓ embedding layer（vocab × hidden 查表）
embeddings: [[0.1, -0.3, ...], [0.5, 0.2, ...]]   ← 向量序列、(seq_len, hidden_dim)
   ↓ Transformer block × N
   ↓ output projection
logits
```

跟 [embedding model](/llm/knowledge-cards/embedding-model/) 的差別：

| 概念                                                     | 用途                                          | 是否獨立訓練 / 部署 |
| -------------------------------------------------------- | --------------------------------------------- | ------------------- |
| Embedding layer（本卡）                                  | LLM 內部第一層、把 token ID 轉向量            | 否、是 LLM 的一部分 |
| [Embedding model](/llm/knowledge-cards/embedding-model/) | 獨立模型、把整段文字轉向量、用於 RAG / 相似度 | 是、獨立模型        |

兩者「都產出向量」、但層級跟用途完全不同：embedding layer 是 LLM 內部結構（per-token、給模型 forward pass 用）、embedding model 是外部工具（per-text、給檢索系統用）。

Embedding layer 的大小：

- Gemma 4 31B：vocab=256K、hidden=5120、embedding matrix ≈ 256K × 5120 = 1.3B 參數
- Llama 3 8B：vocab=128K、hidden=4096、embedding matrix ≈ 0.5B 參數

通常跟 output projection（hidden → vocab）相同大小、有些模型 tied（共用權重）、有些 untied。

## 設計責任

讀模型架構圖看到「token embedding」「embed_tokens」就是這一層。實務意涵：模型大小有非小比例來自 embedding（vocab 越大、embedding 越大）；換 tokenizer 等於整個 embedding 重訓、是 fine-tune 時通常不動的部分。
