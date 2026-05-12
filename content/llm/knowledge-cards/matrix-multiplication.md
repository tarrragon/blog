---
title: "Matrix Multiplication"
date: 2026-05-12
description: "LLM 推論最頻繁的單一運算、forward pass 每層的核心、memory bandwidth 瓶頸的根源"
weight: 1
tags: ["llm", "knowledge-cards", "math", "linear-algebra"]
---

Matrix multiplication（矩陣乘法、matmul、`@`）的核心概念是「**左矩陣的每個 row 跟右矩陣的每個 column 做 [dot product](/llm/knowledge-cards/dot-product/)、結果填進新矩陣**」。對 `A (m × k)` 跟 `B (k × n)`、結果 `C (m × n)`、其中 `C[i][j] = A 第 i row · B 第 j column`。Matmul 是 LLM 推論最頻繁的運算、整個 [forward pass](/llm/knowledge-cards/forward-pass/) 可以看成幾百次 matmul 串起來。

## 概念位置

LLM 中 matmul 出現的關鍵位置：

| 位置                                | 形狀（簡化）                                | 角色                                                          |
| ----------------------------------- | ------------------------------------------- | ------------------------------------------------------------- |
| Embedding lookup                    | `(seq_len, vocab) @ (vocab, hidden)` ≡ 查表 | Token ID → embedding                                          |
| Q/K/V 投影                          | `(seq_len, hidden) @ (hidden, hidden)`      | [Self-attention](/llm/knowledge-cards/self-attention/) 第一步 |
| Attention score                     | `(seq_len, head_dim) @ (head_dim, seq_len)` | Q · K^T、O(n²)、long context 痛點                             |
| Attention output                    | `(seq_len, seq_len) @ (seq_len, head_dim)`  | attention weight · V                                          |
| [FFN](/llm/knowledge-cards/ffn/) up | `(seq_len, hidden) @ (hidden, 4×hidden)`    | FFN 升維、參數大頭                                            |
| FFN down                            | `(seq_len, 4×hidden) @ (4×hidden, hidden)`  | FFN 降維                                                      |
| Output projection                   | `(seq_len, hidden) @ (hidden, vocab)`       | Hidden → logits                                               |

關鍵尺寸規則：**左矩陣 column 數 = 右矩陣 row 數**、即 `(m × k) @ (k × n) = (m × n)`。Dimension mismatch 是訓練 / 推論最常見的 PyTorch 報錯之一。

## 為什麼 matmul 是 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) bound

LLM 推論每生一個 token、要把整份模型權重從記憶體讀到處理器一次（每個權重在當輪 forward pass 的某個 matmul 都用得到）；現代 GPU / Apple Silicon 的算力遠超頻寬、所以「讀權重要多久」變主要瓶頸。這就是為什麼：

- 31B 模型 Q4_K_M 約 18GB、M4 Max 頻寬 546 GB/s、理論上限 ≈ 30 tok/s
- [量化](/llm/knowledge-cards/quantization/) 加速主要是「權重變小、每秒能讀過更多次完整模型」
- [Batching](/llm/knowledge-cards/batching/) / [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 加速主要是「一次讀權重、攤平到多個 token」

## 設計責任

讀 paper / model card 看到模型參數量、可以反推總 matmul 工作量；看到 inference benchmark 看到 tok/s、可以用「模型大小 / memory bandwidth」算理論上限對照。寫 code 場景無需直接寫 matmul、但理解這個運算的成本結構、能看懂量化 / batching / speculative decoding 等加速技巧為什麼有效。
