---
title: "Attention"
date: 2026-05-12
description: "Transformer 內部讓每個 token 對其他 token 加權平均的核心機制、形成 KV cache 跟 context window 的計算基礎"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

Attention 的核心概念是「Transformer 中讓每個 token 對其他 token 加權平均、產生 context-aware 表示」的計算機制。具體運作是用 Query（Q）、Key（K）、Value（V）三組向量算 attention score、再用 softmax 把 score 變成權重、最後加權平均 V。這個機制是 [KV cache](/llm/knowledge-cards/kv-cache/) 概念的源頭、也是 [context window](/llm/knowledge-cards/context-window/) 上限的計算瓶頸。

## 概念位置

Attention 在 [Transformer](/llm/knowledge-cards/transformer/) block 中的位置：

```text
Transformer block：
  ├── Layer Norm
  ├── Attention（本卡聚焦）
  │     ├── Q · K^T → attention score
  │     ├── softmax → weight
  │     └── weight · V → output
  ├── Layer Norm
  └── FFN 層（或 MoE）
```

簡化的計算公式：

```text
attention(Q, K, V) = softmax(Q · K^T / √d) · V
```

Attention 的常見變體（影響 KV cache 體積跟推論性能）：

| 變體                               | 描述                                                                    |
| ---------------------------------- | ----------------------------------------------------------------------- |
| MHA（Multi-Head Attention）        | 原始 Transformer 設計、每 head 獨立 Q / K / V                           |
| GQA（Grouped-Query Attention）     | head group 共用 K / V、KV cache 體積減小、推論較快                      |
| MLA（Multi-head Latent Attention） | DeepSeek 提出、KV cache 壓縮更激進                                      |
| Flash Attention                    | [演算法層的優化實作](/llm/knowledge-cards/flash-attention/)、跟變體獨立 |

## 設計責任

理解 attention 後可以解釋三個現象：為什麼 LLM 推論的記憶體用量隨 [context](/llm/knowledge-cards/context-window/) 長度線性增加（KV cache 是 attention 暫存）、為什麼 [KV cache 量化](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) 對品質影響有不對稱性（K 用於 score 比較、V 用於加權平均、誤差累積方式不同）、為什麼不同 attention 變體在同等模型大小下推論速度差異明顯（KV cache 體積跟卡間頻寬需求不同）。

工程實務上、Attention 是 LLM 推論性能跟記憶體需求的最大來源、量化策略、context 上限、併發數設計都圍繞 attention 跟 KV cache 展開。
