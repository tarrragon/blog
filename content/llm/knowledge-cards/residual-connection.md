---
title: "Residual Connection"
date: 2026-05-12
description: "把 layer 的輸入直接加到輸出上的「跳接」、讓深層網路的梯度能穩定回流"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "training"]
---

Residual connection（殘差連接、skip connection）的核心概念是「把 layer 的輸入直接加到輸出上」、形式是 `output = layer(x) + x`。這個簡單加法解決了深層網路的訓練退化問題：沒有 residual、模型加深會反而變差（不是過擬合、是 [gradient](/llm/knowledge-cards/gradient/) 在反向傳播中衰減太多）；有 residual、訓練幾十甚至上百層都穩。

## 概念位置

Residual connection 在 Transformer block 中出現兩次：

```text
Transformer block：
  x
  ├──────────────┐  ← skip connection（保留原始 x）
  ↓              │
  LayerNorm      │
  ↓              │
  Self-Attention │
  ↓              │
  +←─────────────┘  ← residual add：attention output + x
  │
  ├──────────────┐  ← skip connection（保留 attention 後的值）
  ↓              │
  LayerNorm      │
  ↓              │
  FFN            │
  ↓              │
  +←─────────────┘  ← residual add：FFN output + previous
  ↓
  進入下一個 block
```

關鍵性質：

1. **Gradient 可以走捷徑**：[Backpropagation](/llm/knowledge-cards/backpropagation/) 時、gradient 能透過 skip connection 直接傳回淺層、避免 chain rule 累積衰減。
2. **Layer 學「殘差」而不是「完整轉換」**：每層學「該怎麼微調輸入」、不用學「從零生成輸出」、優化更容易。
3. **跟 [LayerNorm](/llm/knowledge-cards/layer-normalization/) 配對**：兩者一起是深層 Transformer 訓得起來的基礎。

## 設計責任

理解 residual connection 後可以判讀 Transformer 能堆幾十層的根本原因（不是因為 attention、是因為 residual + LayerNorm 讓深層仍可訓練）；也能看懂 ResNet、ViT 等其他用 residual 架構的設計。LLM 推論時 residual 不算 bottleneck、但在訓練 / fine-tune 時、residual 是 gradient flow 健康度的關鍵。
