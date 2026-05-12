---
title: "RoPE（Rotary Position Embedding）"
date: 2026-05-12
description: "用旋轉矩陣把位置資訊直接旋轉進 Q/K 向量、現代 LLM 主流的位置編碼方式"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

RoPE（Rotary Position Embedding、旋轉位置編碼、Su et al., 2021）的核心概念是「**把 token 在序列中的位置資訊用旋轉矩陣直接旋轉進 Q 跟 K 向量裡**、不是用加法疊加另一個 embedding」。RoPE 是 Llama、Gemma、Qwen、Mistral 等現代 LLM 的標配、相對早期的 absolute / learned positional embedding 有更好的長 context 推廣性。

## 概念位置

位置編碼的演化路線：

| 方法                       | 機制                                                             | 主要問題                                                         |
| -------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- |
| Absolute（原 Transformer） | 用 sin/cos 函數產生固定 position embedding、加到 token embedding | 訓練長度外推性差                                                 |
| Learned absolute（GPT-2）  | 每個位置學一個可訓練向量、加到 token embedding                   | 超過訓練長度完全沒對應 embedding                                 |
| Relative                   | attention 算分數時加上「相對位置」的 bias                        | 實作複雜、跟 [KV cache](/llm/knowledge-cards/kv-cache/) 兼容性差 |
| **RoPE**                   | 用旋轉矩陣把位置旋轉進 Q/K（不動 V）                             | 主流、長 context 推廣性好（配 scaling）                          |

RoPE 的核心數學（簡化）：

```text
傳統：token at position m 的 Q 是 Q_m = x_m @ W_Q
RoPE：Q_m = R(m) × (x_m @ W_Q)  ← R(m) 是依位置 m 決定的旋轉矩陣

attention score = Q_m @ K_n^T
               = R(m) × q × (R(n) × k)^T
               = q × R(m - n) × k^T  ← 只依賴相對位置 (m-n)！
```

關鍵性質：RoPE 算出的 attention score 只依賴**相對位置**、所以推廣到比訓練長度更長的 context 時有自然的數學基礎、配合 RoPE scaling（YaRN、NTK-aware、Position Interpolation）就能把 8K 訓練的模型擴展到 128K / 1M context。

## 設計責任

讀 model card 看到 `rope_theta: 10000`、`rope_scaling: {type: yarn, factor: 8}` 等就是 RoPE 配置。寫 code 場景的意涵：long context 模型（如 Llama 3 128K）的推廣能力主要靠 RoPE + scaling、不是直接訓練 128K 全長；但聲稱 context 跟「實用 context」仍有差距、長 context 上模型表現會逐步衰減。
