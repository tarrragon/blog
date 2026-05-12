---
title: "Forward Pass"
date: 2026-05-12
description: "input 經過所有 layer 的計算、得到 output 的單向流程；推論跟訓練都會跑、訓練多一個反向階段"
weight: 1
tags: ["llm", "knowledge-cards", "inference", "training"]
---

Forward pass（前向傳播）的核心概念是「input 從第一層算到最後一層、得到 output 的單向計算流程」。LLM 推論時生成一個 [token](/llm/knowledge-cards/token/)、就是跑一次 forward pass；訓練時、每個 batch 也都先跑 forward pass 算出 [loss](/llm/knowledge-cards/loss-function/)、再跑 [backpropagation](/llm/knowledge-cards/backpropagation/) 算 gradient。

## 概念位置

LLM 一次 forward pass 的大略流程：

```text
input token IDs
  ↓ embedding layer：整數 → 向量
sequence of vectors
  ↓ Transformer block 1（attention + FFN）
  ↓ Transformer block 2
  ↓ ...
  ↓ Transformer block N
final hidden state
  ↓ output projection（hidden → vocab）
logits（每個 vocab token 一個分數）
  ↓ softmax（推論時）
probability distribution → 挑下一個 token
```

跟相關概念的對比：

| 概念                                                               | 跟 forward pass 的關係                                       |
| ------------------------------------------------------------------ | ------------------------------------------------------------ |
| [Prefill](/llm/knowledge-cards/prefill/)                           | Prompt 階段的「一次性 forward pass」、所有 prompt token 並行 |
| Decode 階段                                                        | 每生一個 token 跑一次 forward pass、序列化、慢               |
| [Speculative decoding](/llm/knowledge-cards/speculative-decoding/) | 一次 forward pass 同時驗證多個猜測 token                     |
| [Backpropagation](/llm/knowledge-cards/backpropagation/)           | 訓練時 forward pass 的反向延伸、推論不需要                   |

## 設計責任

理解 forward pass 後可以判讀 LLM 的記憶體與速度：每次 forward pass 都要把整份模型權重從記憶體讀到處理器一次、所以 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 是推論瓶頸；[KV cache](/llm/knowledge-cards/kv-cache/) 的存在是為了避免每次 forward pass 重算前面 token 的 K/V；MTP / speculative decoding 都是「一次 forward pass 攤平多個 token 成本」的優化路徑。
