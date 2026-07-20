---
title: "BPE（Byte-Pair Encoding）"
date: 2026-05-12
description: "用「最常一起出現的字元對」合併建詞彙表的 tokenization 演算法、GPT / Llama 等主流"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

BPE（Byte-Pair Encoding、Sennrich et al., 2015 引入 NLP）的核心概念是「**從字元開始、反覆找『出現頻率最高的字元對』把它合併成新 [token](/llm/knowledge-cards/token/)、直到達到目標詞彙表大小**」。是 GPT、Llama、Mistral 等主流 LLM 的 tokenization 演算法、能在「字元」跟「整詞」之間找平衡。

## 概念位置

BPE 訓練 tokenizer 的流程（簡化）：

```text
Step 0：vocab = 所有單一字元（256 個 byte / Unicode 字符）

迭代：
  Step 1：掃描 corpus、統計所有相鄰 token 對的出現頻率
  Step 2：找出現最多的字元對（如 "l" + "o" 一起出現 1M 次）
  Step 3：把它當新 token 加進 vocab、把 corpus 裡所有這個對換成新 token
  Step 4：回到 Step 1、直到 vocab 達到目標大小（如 50K、128K、256K）
```

實際 [token](/llm/knowledge-cards/token/) 化的結果：

| 文字              | BPE token 化結果                    | 理由                                |
| ----------------- | ----------------------------------- | ----------------------------------- |
| `Hello`           | `["Hello"]`                         | 高頻單字、整詞當一個 token          |
| `Hellobot`        | `["Hello", "bot"]`                  | 罕見組合、拆成已知 token            |
| `Antidisestab...` | `["Anti", "dis", "establish", ...]` | 罕見長詞、拆成 sub-word             |
| `你好`            | `["你", "好"]` 或 `["你好"]`        | 視 tokenizer 訓練 corpus 的中文比例 |

BPE 的變體：

1. **Byte-level BPE**：把每個 byte 當基底（256 個）、所以任何 Unicode / 二進制都能 tokenize、不會有 unknown token。GPT-2 開始的標準。
2. **[SentencePiece](/llm/knowledge-cards/sentencepiece/) BPE**：跟 SentencePiece 框架結合、處理多語言更靈活。

## 設計責任

讀 model card 看到 `tokenizer: BPE` 就是這個演算法。BPE 對英文友好（高頻單詞整個一 token）、中文 / 日韓較不友好（單字符常被當獨立 token）；這就是為什麼同一段中文翻譯成英文後、英文 token 數常常更少、雲端 LLM 用中文 API 比英文貴。但越新的模型（Gemma 4、Qwen3 等）vocab 越大（256K+）、對中文友善度提升中。
