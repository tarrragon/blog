---
title: "FFN（Feed-Forward Network）"
date: 2026-05-12
description: "Transformer block 內部的兩層 linear + activation、佔模型參數量的多數"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

FFN（Feed-Forward Network、前饋網路）的核心概念是「Transformer block 中 attention 後面的兩層 linear + [activation function](/llm/knowledge-cards/activation-function/) 結構」。FFN 是 LLM 中**參數量最大**的元件、典型 Transformer block 裡 FFN 約佔 2/3 參數、attention 約佔 1/3。

## 概念位置

標準 FFN 的計算：

```text
input（hidden_dim）
  ↓ W_up（linear、hidden_dim → intermediate_dim、通常放大 4x）
intermediate vector
  ↓ activation function（ReLU / GELU / SwiGLU）
  ↓ W_down（linear、intermediate_dim → hidden_dim）
output（hidden_dim）
```

Intermediate dim 通常是 hidden dim 的 4 倍（例如 hidden=4096、intermediate=16384）、所以 FFN 的參數量是 `hidden × intermediate × 2 ≈ 8 × hidden²`、遠大於 attention 的 `4 × hidden²`（Q/K/V/O 四個 hidden × hidden 矩陣）。

FFN 變體：

| 變體       | 結構特性                                 | 出現在                                |
| ---------- | ---------------------------------------- | ------------------------------------- |
| 標準 FFN   | 兩個 linear + 一個 activation            | 早期 Transformer、BERT、GPT-2         |
| SwiGLU FFN | 三個 linear（gate + up + down）+ Swish   | Llama、Gemma、Qwen 主流               |
| MoE FFN    | 多個「expert」FFN、每個 token 只啟用幾個 | [MoE](/llm/knowledge-cards/moe/) 模型 |

## 設計責任

理解 FFN 是參數大頭、能解釋幾件事：[MoE](/llm/knowledge-cards/moe/) 為什麼是「把 FFN 換成多個專家、只啟用部分」（因為 FFN 是最值得稀疏化的部分）、[MoE CPU offload](/llm/knowledge-cards/moe-cpu-offload/) 為什麼是「把 expert FFN 卸到 RAM」（FFN 大、卸下來省 VRAM）、為什麼模型大小用「參數量」算（FFN 主導）。LoRA fine-tuning 時、通常選擇對 attention 的 Q/V 投影做 LoRA、不對 FFN 動、因為 FFN 太大、LoRA 收益相對小。
