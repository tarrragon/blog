---
title: "Pre-training"
date: 2026-05-12
description: "LLM 訓練的第一階段：用 trillion-token 級網路文字做 next-token prediction、得到 base model"
weight: 1
tags: ["llm", "knowledge-cards", "training"]
---

Pre-training（預訓練）的核心概念是「在大量未標註文字上、用 next-token prediction 當目標訓練一個語言模型」。產出的權重稱為 [base model](/llm/knowledge-cards/base-model/)、是後續 [SFT](/llm/knowledge-cards/sft/) / [RLHF](/llm/knowledge-cards/rlhf/) 的起點。Pre-training 是 LLM 三階段訓練流程中**最貴、最耗時、最決定模型上限**的階段。

## 概念位置

Pre-training 在 LLM 訓練 pipeline 的位置：

```text
[網路文字 / 書籍 / code / 論文]（trillion token 級）
   ↓ Pre-training（next-token prediction、cross-entropy loss）
[Base model]：會接龍但不會對話
   ↓ SFT（指令-回答對資料）
[Instruction-tuned model]：會跟指令走
   ↓ RLHF / DPO（人類偏好資料）
[Aligned model]：對話風格 / 安全性對齊
```

Pre-training 的特性：

| 維度     | 典型數字（2026 年主流大模型）                                                                                         |
| -------- | --------------------------------------------------------------------------------------------------------------------- |
| 資料量   | 數兆 token（Common Crawl、RefinedWeb、The Pile、Stack 等）                                                            |
| GPU 用量 | 數百到數萬張 H100 / B200、並行訓練                                                                                    |
| 訓練時間 | 數週到數月                                                                                                            |
| 成本級別 | 數百萬到數億美元                                                                                                      |
| Loss     | [Cross-entropy](/llm/knowledge-cards/cross-entropy/) on next-token                                                    |
| 結果     | 「會接龍」的 [base model](/llm/knowledge-cards/base-model/)、可用 [perplexity](/llm/knowledge-cards/perplexity/) 評估 |

## 設計責任

理解 pre-training 後可以判讀幾件事：模型的「世界知識」絕大部分在 pre-training 時就決定了、[SFT](/llm/knowledge-cards/sft/) / [RLHF](/llm/knowledge-cards/rlhf/) 只是「教模型怎麼用這些知識回答」、不會大幅增加新知識；模型 cutoff date 就是 pre-training 資料的截止；想做新領域知識引入、[RAG](/llm/knowledge-cards/rag/) 比繼續 fine-tune 划算（pre-training 太貴、且 fine-tune 容易讓既有能力退化）。
