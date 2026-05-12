---
title: "Contrastive Learning"
date: 2026-05-12
description: "用「相關 vs 不相關」成對 / 三元組樣本訓練 embedding 的方法、現代 embedding model 的核心訓練 paradigm"
weight: 1
tags: ["llm", "knowledge-cards", "embedding", "training"]
---

Contrastive learning（對比學習）的核心概念是「**訓練模型讓相關樣本的 embedding 在向量空間中靠近、無關樣本遠離**」。是現代 [embedding model](/llm/knowledge-cards/embedding-model/) 的標準訓練 paradigm、跟 LLM pretrain 的 next-token prediction 完全不同的訓練目標。

## 概念位置

Contrastive learning 的核心訓練形態：

```text
正向對（positive pair）：
  (query, relevant_doc) — 應該在 embedding 空間靠近
  例：("Python how to read file", "Python file reading tutorial...")

負向對（negative pair）：
  (query, irrelevant_doc) — 應該在 embedding 空間遠離
  例：("Python how to read file", "CSS flexbox guide...")

Loss（簡化的 InfoNCE loss）：
  pull positive pair 靠近
  push negative pair 遠離（多個 negative samples 對比）
```

主流形式：

| 形式                         | Loss 設計                                                                 | 代表模型                   |
| ---------------------------- | ------------------------------------------------------------------------- | -------------------------- |
| Triplet loss                 | (anchor, positive, negative)、要求 anchor-positive 距離 < anchor-negative | 早期 sentence-BERT         |
| InfoNCE / NCE                | Cross-entropy over batch、把 batch 內其他樣本當 hard negative             | OpenAI ada-002、bge 系列   |
| MultipleNegativesRankingLoss | 上述變體、用 batch 內隨機其他樣本當 negative                              | Sentence-Transformers 主流 |

關鍵特性：

1. **資料量需求大**：contrastive learning 需要億級的正向對才能訓出好 embedding；資料來源是 query-doc click log、StackExchange QA pair、CC-paraphrase 等
2. **Hard negative mining 是品質關鍵**：隨機選 negative 容易（從 batch 取就行）、找「看似相關但實際無關」的 hard negative 更挑戰、是 embedding quality 提升的關鍵
3. **不能直接拿 pretrained LLM 用**：LLM 的 hidden state 不是「為 retrieval 優化」的、要再 fine-tune 一輪 contrastive learning 才能當 embedding model

## 設計責任

讀 embedding model paper / 訓練 code 看到「InfoNCE」「triplet」「hard negatives」「mining strategy」就是這 paradigm。寫 code 場景的判讀：

1. **挑 embedding model 看訓練資料 domain**：通用 retrieval（如 bge-large、nomic-embed）vs code-specific（如 jina-embeddings-v2-code、CodeT5+）、訓練資料分佈影響大
2. **不能拿任意 LLM 抽 hidden state 當 embedding**：如「Llama 的 last hidden state 當 embedding」這類做法在 retrieval 上通常顯著輸給專門 contrastive-trained embedding model
3. **Fine-tune embedding model 通常用 LoRA + contrastive loss**：在自己 domain 資料上 fine-tune、提升 in-domain retrieval；標準 pipeline 是 sentence-transformers + LoRA
