---
title: "MTEB"
date: 2026-05-12
description: "Massive Text Embedding Benchmark：8 大類 56 任務、評估 embedding model 跨任務通用能力的標準"
weight: 1
tags: ["llm", "knowledge-cards", "embedding", "evaluation"]
---

MTEB（Massive Text Embedding Benchmark、Muennighoff et al., 2022）的核心概念是「**評估 [embedding model](/llm/knowledge-cards/embedding-model/) 跨多種任務通用能力的標準 benchmark**」。覆蓋 8 大類任務（classification、clustering、pair classification、reranking、retrieval、STS、summarization、bitext mining）、56 個 dataset、112 種語言。是現在挑選 embedding model 最常用的 leaderboard。

## 概念位置

MTEB 的 8 大任務類別：

| 類別                               | 任務本質                               | 衡量                                                        |
| ---------------------------------- | -------------------------------------- | ----------------------------------------------------------- |
| Classification                     | 用 embedding 做下游分類（如情感分析）  | 分類 accuracy                                               |
| Clustering                         | 把相似 doc 聚到一起                    | V-measure、NMI                                              |
| Pair classification                | 判斷兩段文字「相關 / 不相關」          | F1、AP                                                      |
| **Reranking**                      | 對 retrieval 結果用 embedding 重新排序 | mAP、MRR                                                    |
| **Retrieval**                      | 給 query、從大量 corpus 找相關 doc     | nDCG@10、[Recall@k](/llm/knowledge-cards/retrieval-recall/) |
| STS（Semantic Textual Similarity） | 預測句對相似度（連續分數）             | Spearman correlation                                        |
| Summarization                      | embedding-based summary quality        | Correlation with human rating                               |
| Bitext mining                      | 跨語言找翻譯對                         | F1                                                          |

**對寫 code / RAG 場景最相關**：Retrieval、Reranking 兩類（粗體）。其他類別反映通用能力、但不直接影響 RAG 應用品質。

主流 embedding model 在 MTEB Retrieval 的代表性能（2026/5 估計、會持續變動）：

| 模型                          | 模型大小 | MTEB Retrieval avg | 適合場景                      |
| ----------------------------- | -------- | ------------------ | ----------------------------- |
| BAAI/bge-large-en-v1.5        | ~335M    | ~55                | 開源通用、英文 retrieval 主力 |
| nomic-embed-text-v1.5         | ~137M    | ~52                | 開源、小巧、Ollama 內建       |
| jina-embeddings-v3            | ~570M    | ~58                | 開源、多語、code 友善         |
| mxbai-embed-large-v1          | ~335M    | ~55                | 開源通用                      |
| OpenAI text-embedding-3-large | API only | ~64                | 雲端旗艦                      |
| voyage-3                      | API only | ~62                | 雲端、Anthropic 推薦          |

> **事實查核註**：MTEB 數字依模型版本、評估配置變動、上述為 2026/5 大致排名、引用前以 [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) 當前狀態為準。

## 設計責任

讀 embedding model 比較看到「MTEB score」就是這 benchmark。寫 code / RAG 場景的判讀：

1. **看 Retrieval 子分數、不是 overall**：MTEB overall 含 8 類、跟 RAG 場景關係最大的是 Retrieval 子分；通用 retrieval 分數高、reranking 分數高、就值得試
2. **跟自己 domain 對齊**：MTEB 多為通用語料、自己 domain（如 code、medical、legal）可能跟 MTEB 落差大；in-domain benchmark 比 MTEB 更重要
3. **大小 / 速度 / 品質 trade-off**：bge-large（335M）vs nomic-embed（137M）、後者跑得快、適合本地 RAG；前者品質略高、適合雲端或 latency 不敏感場景
4. **MTEB 高分不代表「適合你」**：高分模型可能是 instruction-tuned embedding（query 需要加特定前綴）、用法跟簡單模型不同、要看 model card
