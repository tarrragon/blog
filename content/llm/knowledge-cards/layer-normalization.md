---
title: "Layer Normalization"
date: 2026-05-12
description: "在每個 token 的 hidden state 上做正規化（減 mean、除 std）、穩定深層網路訓練"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "training"]
---

Layer normalization（LayerNorm）的核心概念是「對單一 token 的 hidden state 向量做正規化」——把該向量的 mean 移到 0、std 縮到 1、再用兩個可學參數做仿射變換。它是 [Transformer](/llm/knowledge-cards/transformer/) 穩定深層訓練的關鍵元件、跟 batch normalization 的差別是「正規化軸不同」、LayerNorm 對單個 sample 內部做、不依賴 batch 統計。

## 概念位置

LayerNorm 在 Transformer block 內的位置（現代主流是 pre-norm）：

```text
Transformer block（pre-norm 配置）：
  x
  ↓ LayerNorm
  ↓ Self-Attention
  ↓ + 跟 x 做 residual connection
  ↓ LayerNorm
  ↓ FFN
  ↓ + 跟前一步輸出做 residual connection
```

主流變體比較：

| 變體      | 計算                                  | 出現在                          |
| --------- | ------------------------------------- | ------------------------------- |
| LayerNorm | `(x - mean) / std × γ + β`            | 早期 Transformer（GPT-2、BERT） |
| RMSNorm   | `x / rms(x) × γ`（不減 mean、不加 β） | Llama、Gemma、Qwen 等主流       |

RMSNorm 比 LayerNorm 簡單、實測訓練穩定性接近、推論更快（少算 mean 跟加 β）、所以現代 LLM 多用 RMSNorm。讀 paper 看到「RMSNorm」就是 LayerNorm 的這個簡化變體。

Pre-norm vs post-norm：

- **Pre-norm**（LayerNorm 在 attention / FFN 之前）：深度模型訓練較穩、現代主流。
- **Post-norm**（LayerNorm 在 residual add 之後）：原始 Transformer paper 的設計、深層訓練不穩定。

Pre-norm 能撐住幾十層 Transformer、關鍵在於跟 [residual connection](/llm/knowledge-cards/residual-connection/) 搭配、讓梯度能穩定流過每一層。

## 設計責任

理解 LayerNorm 後可以判讀「深層 LLM 為什麼訓得起來」的部分答案：[residual connection](/llm/knowledge-cards/residual-connection/) + LayerNorm 是讓梯度能穩定流過幾十層 Transformer 的兩根支柱。讀 model card 看到「RMSNorm」「pre-norm」等詞、知道對應的設計選擇跟訓練穩定性意涵。
