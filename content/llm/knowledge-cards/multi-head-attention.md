---
title: "Multi-Head Attention"
date: 2026-05-12
description: "把 attention 切成多個 head 並行計算、讓模型能同時注意多種模式"
weight: 1
tags: ["llm", "knowledge-cards", "transformer", "architecture"]
---

Multi-Head Attention（MHA、多頭注意力）的核心概念是「把 [self-attention](/llm/knowledge-cards/self-attention/) 的 Q/K/V 投影切成多個獨立的 **head**、各自算 attention、最後再 concat 起來」。直覺：每個 head 可以學會關注不同類型的關係（語法 / 語意 / 位置 / 共指 etc.）、比單一 attention 表達能力強。

## 概念位置

MHA 的計算結構：

```text
輸入 hidden state（dim = 4096）
   ↓ 投影成 Q/K/V、每個切成 h 個 head（如 h=32、每個 head 128 維）
Head 1：Q_1、K_1、V_1 → attention_1（128 維）
Head 2：Q_2、K_2、V_2 → attention_2
...
Head h：Q_h、K_h、V_h → attention_h
   ↓ concat 所有 head 輸出（h × 128 = 4096）
   ↓ output projection（4096 → 4096）
最終輸出
```

多頭變體：MHA → GQA → MLA 是 KV cache 體積壓縮的演化方向。

| 變體                               | Q head 數 | K/V head 數                        | [KV cache](/llm/knowledge-cards/kv-cache/) 體積 | 出現在                           |
| ---------------------------------- | --------- | ---------------------------------- | ----------------------------------------------- | -------------------------------- |
| MHA（Multi-Head Attention）        | h         | h                                  | 100%（基準）                                    | 原始 Transformer、GPT-3、Llama 1 |
| MQA（Multi-Query Attention）       | h         | 1（所有 head 共用）                | 1/h                                             | PaLM、Falcon                     |
| GQA（Grouped-Query Attention）     | h         | h/g（每 g 個 Q head 共用一組 K/V） | 1/g                                             | Llama 2 / 3、Mistral、Gemma      |
| MLA（Multi-head Latent Attention） | h         | 用 latent 壓縮再展開               | 更激進壓縮                                      | DeepSeek-V2 / V3                 |

## 設計責任

讀 model card 看到 `num_attention_heads: 32`、`num_key_value_heads: 8` 等就是 MHA / GQA 設定（Q=32、K/V=8 表示 GQA、g=4）。寫 code 場景的意涵：GQA / MLA 的 [KV cache](/llm/knowledge-cards/kv-cache/) 體積小、長 context / 高併發場景更友善、是現代 LLM 大量採用的設計。
