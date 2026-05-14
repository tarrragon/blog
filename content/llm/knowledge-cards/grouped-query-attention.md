---
title: "Grouped-Query Attention"
date: 2026-05-14
description: "讓多個 query head 共用較少的 key/value head，以降低 KV cache 體積與推論記憶體壓力"
weight: 1
tags: ["llm", "knowledge-cards", "attention", "kv-cache"]
---

Grouped-query attention（GQA）的核心概念是「**多個 query head 共用較少的 key/value head**」。它介於 Multi-Head Attention 與 Multi-Query Attention 之間，用較小的品質代價換取更小的 [KV cache](/llm/knowledge-cards/kv-cache/) 與更好的長 context serving 效率。

## 概念位置

GQA 是 [multi-head attention](/llm/knowledge-cards/multi-head-attention/) 的推論友善變體。MHA 是每個 query head 都有自己的 K/V；MQA 是所有 query head 共用一組 K/V；GQA 則把 query head 分組，每組共用 K/V。

## 可觀察訊號與例子

在 model config 裡看到 `num_attention_heads: 32`、`num_key_value_heads: 8`，代表 32 個 Q head 共用 8 組 K/V head，group size 是 4。這會讓 KV cache 約縮到 MHA 的四分之一，長 context 與高併發更友善。

## 設計責任

選模型或估算 serving 成本時，要看 `num_key_value_heads`，而不是只看總參數。GQA 對本地推論特別重要，因為 [context window](/llm/knowledge-cards/context-window/) 與併發數常被 KV cache 卡住。
