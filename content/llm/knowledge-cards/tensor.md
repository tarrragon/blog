---
title: "Tensor"
date: 2026-05-12
description: "多維陣列、矩陣是 2D 特例、PyTorch / MLX / JAX 等 framework 的核心型別"
weight: 1
tags: ["llm", "knowledge-cards", "math", "linear-algebra"]
---

Tensor（張量）的核心概念是「**N 維陣列**」。Scalar 是 0D tensor、vector 是 1D、matrix 是 2D、再往上加維度就是 3D、4D。PyTorch、MLX、JAX、TensorFlow 等所有深度學習 framework 的核心型別都叫 Tensor、所有 LLM 內部運算（[matrix multiplication](/llm/knowledge-cards/matrix-multiplication/)、[softmax](/llm/knowledge-cards/softmax/)、[layer norm](/llm/knowledge-cards/layer-normalization/) 等）都對 tensor 做。

## 概念位置

LLM 中常見的 tensor 維度：

| 維度 | shape                                        | 意義                                                        | 出現在                                                      |
| ---- | -------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------- |
| 1D   | `(vocab_size,)`                              | 一個 token 位置的 [logit](/llm/knowledge-cards/logit/) 向量 | Output layer 輸出                                           |
| 2D   | `(seq_len, hidden_dim)`                      | 一個 sequence 的 hidden state                               | 每個 Transformer block 內部                                 |
| 3D   | `(batch_size, seq_len, hidden_dim)`          | 一個 batch 的多個 sequence                                  | Batched 推論 / 訓練                                         |
| 4D   | `(batch_size, num_heads, seq_len, head_dim)` | Multi-head attention 的並行結構                             | [Self-attention](/llm/knowledge-cards/self-attention/) 內部 |
| 5D+  | `(batch, heads, seq, head_dim, ...)`         | 罕見、特殊架構                                              | MoE expert dispatch、特殊 attention                         |

關鍵運算：

1. **Reshape**：改 shape 但不變資料總量、如 `(batch, seq, hidden) → (batch * seq, hidden)`。
2. **Transpose / permute**：交換維度順序、attention 計算前後常用。
3. **Broadcasting**：不同 shape 的 tensor 自動擴展配對、如 `(seq, hidden) + (hidden,)`。
4. **Indexing / slicing**：抽出子 tensor、如 `tensor[:, -1, :]` 取最後一個 token 的 hidden。

## 設計責任

讀 PyTorch / MLX 推論 / 訓練 code 看到 `torch.Tensor`、`mx.array`、`tf.Tensor` 等就是這個型別、所有 LLM 運算都建在它上面。寫 code 場景的判讀：報錯訊息看到 `shape mismatch` / `size of dimension X` 通常是 tensor 維度配錯；[KV cache](/llm/knowledge-cards/kv-cache/) 內部存的就是 4D tensor `(num_layers, 2, batch, num_kv_heads, seq, head_dim)` 之類的結構、量化 KV cache 就是改這個 tensor 的 dtype。
