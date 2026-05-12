---
title: "Self-Attention"
date: 2026-05-12
description: "Q / K / V 都從同一個 sequence 投影出來的 attention、Transformer 的標誌性設計"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

Self-attention 的核心概念是「Query / Key / Value 三組向量都從**同一個** sequence 投影出來的 [attention](/llm/knowledge-cards/attention/)」。對比下、cross-attention 的 Q 來自一個 sequence、K/V 來自另一個 sequence（如 encoder-decoder 的 decoder 看 encoder）。LLM（decoder-only）每層都是 self-attention、self-attention 是 Transformer 「讓每個 token 看到序列其他 token」的機制本身。

## 概念位置

Self-attention 的計算步驟：

```text
輸入 sequence: x_1, x_2, ..., x_n（每個是向量）

對每個 token i：
  Q_i = x_i × W_Q   ← Query：「我要找什麼樣的資訊」
  K_i = x_i × W_K   ← Key：「我提供什麼樣的資訊」
  V_i = x_i × W_V   ← Value：「我的實際內容」

attention(Q_i, K, V) = softmax(Q_i · K^T / √d) · V
                       └─ Q 跟所有 K 算分數、決定權重 ─┘
                                                       └─ 加權平均所有 V ─┘
```

關鍵特性：

1. **Q / K / V 來源相同**：跟 cross-attention 區分；都從同一個輸入 sequence 投影。
2. **每個 token 都跟所有 token 算一次**：複雜度 O(n²)、是 long context 痛點根源。
3. **Causal mask 在 self-attention 內生效**：LLM 的 [decoder-only](/llm/knowledge-cards/transformer/) self-attention 加 causal mask、token i 只能看 1~i、不能看 i+1 以後（不能偷看未來）。

## 設計責任

理解 self-attention 後可以判讀幾件 LLM 設計事：[KV cache](/llm/knowledge-cards/kv-cache/) 為什麼有效（自回歸生成時、過去 token 的 K/V 不變、存下來下次直接用）；MHA / GQA / MLA 等變體在動什麼（共享 / 壓縮 K/V 投影、不動 Q）；為什麼長 context 推論慢（self-attention 的 O(n²) 計算）。
