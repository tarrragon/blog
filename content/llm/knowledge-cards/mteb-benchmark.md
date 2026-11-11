---
title: "MTEB"
date: 2026-05-12
description: "Massive Text Embedding Benchmark：8 大類 56 任務、評估 embedding model 跨任務通用能力的標準"
weight: 1
tags: ["llm", "knowledge-cards", "embedding", "evaluation"]
---

MTEB（Massive Text Embedding Benchmark、Muennighoff et al., 2022）的核心概念是「**評估 [embedding model](/llm/knowledge-cards/embedding-model/) 跨多種任務通用能力的標準 benchmark**」。覆蓋 8 大類任務（classification、clustering、pair classification、reranking、retrieval、STS、summarization、bitext mining）、56 個 dataset、112 種語言。是現在挑選 embedding model 最常用的 leaderboard。

## 跟其他概念的關係

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

## 判斷條件與後果

MTEB 分數是否能拿來挑 RAG 用的 embedding model，看比的是哪一個分數、評估語料跟自己的 domain 有多接近：

- **比 overall 分數時**：overall 平均了 8 類任務，跟 RAG 直接相關的只有 Retrieval 與 Reranking 兩類，overall 高的模型在 RAG 裡的表現仍取決於它的 Retrieval 子分；兩個子分都高的模型才是 RAG 的候選。
- **自己的 domain 離通用語料越遠時**（code、medical、legal）：MTEB 多為通用語料，排名跟自己資料上的檢索品質可能落差很大，這時用自己資料做的 in-domain benchmark 才分得出高下。
- **在模型大小之間選時**：nomic-embed（137M）跑得快，適合本地 RAG；bge-large（335M）品質略高，適合雲端或 latency 不敏感的場景。
- **高分模型是 instruction-tuned embedding 時**：query 要加特定前綴，用法跟簡單模型不同，照簡單模型的方式呼叫時拿不到它在 leaderboard 上的表現，前綴的寫法在它的 model card。
