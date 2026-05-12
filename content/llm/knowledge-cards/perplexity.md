---
title: "Perplexity"
date: 2026-05-12
description: "cross-entropy 的指數形式、直覺意義為「模型平均覺得下個 token 有多少種可能」"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "math"]
---

Perplexity（困惑度）的核心概念是「[cross-entropy](/llm/knowledge-cards/cross-entropy/) 的指數形式」：`perplexity = exp(cross-entropy)`。直覺意義是「模型在每個位置平均覺得下個 [token](/llm/knowledge-cards/token/) 有多少種候選」。perplexity = 1 表示模型完美預測；perplexity = vocab_size 表示模型純猜（vocab 上的 uniform 分佈）。

## 概念位置

Perplexity 跟 cross-entropy 的關係：

| 指標          | 公式 / 定義                     | 人類直覺                   |
| ------------- | ------------------------------- | -------------------------- |
| Cross-entropy | `-mean(log p_true)`、底通常是 e | loss 數字、訓練拿來最佳化  |
| Perplexity    | `exp(cross-entropy)`            | 「平均看到幾種候選」、好讀 |

換算範例（base e）：

| Cross-entropy | Perplexity | 意義（極粗略直覺）              |
| ------------- | ---------- | ------------------------------- |
| 11            | ~60K       | 純隨機（vocab ≈ 128K 時）       |
| 5             | ~148       | 早期訓練                        |
| 3             | ~20        | 中等訓練模型                    |
| 2             | ~7.4       | 接近現代成熟 LLM 在文本上的表現 |
| 0             | 1          | 完美預測（不可能達到）          |

Perplexity 主要用於：

- **預訓練評估**：在 held-out 語料上算 perplexity、衡量基礎建模能力。
- **量化品質衡量**：fp16 vs Q4 vs Q3 模型的 perplexity 差異、看量化造成多少品質損失。
- **領域 benchmark**：在特定領域語料（code、math、医學文獻）上算 perplexity、評估模型對該領域的熟悉度。

## 設計責任

Perplexity 是 base model 評估標準、但對 instruction-tuned / chat 模型用處有限（chat 模型輸出風格已偏離 raw text、perplexity 不一定降）。對寫 code 場景的判讀：看到 paper 報 perplexity 是評估 pretrain 品質的訊號、實際聊天 / coding 能力要看 [SWE-bench](/llm/knowledge-cards/swe-bench/)、MMLU、HumanEval 等任務式 benchmark。
