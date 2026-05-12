---
title: "Hybrid Search"
date: 2026-05-12
description: "把字面 retrieval（BM25）跟語意 retrieval（embedding）的結果用 RRF 等方法合併、補單一路線的盲點"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Hybrid search 的核心概念是「**同時跑字面 retrieval（BM25 / tf-idf）跟語意 retrieval（embedding similarity）、用 Reciprocal Rank Fusion 等方法合併結果**」。補單一路線的盲點：BM25 抓不到語意相似（同義詞 / 不同表述）、embedding 抓不到精確 keyword（術語 / 識別碼 / 罕見 entity）。是 production RAG 的標配。

## 概念位置

兩條 retrieval 路線的盲點：

| 場景                                          | BM25（字面） | Embedding（語意）          |
| --------------------------------------------- | ------------ | -------------------------- |
| Query / doc 共用 keyword                      | ✅ 強        | ✅ 強                      |
| Query 用同義詞、doc 用另一字                  | ❌ 找不到    | ✅                         |
| Query 用通俗、doc 用 jargon                   | ❌ 找不到    | ✅                         |
| 精確 keyword（如 product code、UUID、API 名） | ✅           | ❌ 可能漂掉                |
| 罕見 entity（人名 / 地名）                    | ✅           | ❌（embedding model 不熟） |
| Embedding model 不熟的 domain                 | ✅           | ❌ 表現崩                  |

主流合併方法：

### Reciprocal Rank Fusion（RRF）

最常用、簡單：

```text
對每個 doc：
  score = sum_over_retrievers(1 / (k + rank_i))

k 是常數（典型 60）、rank 是該 retriever 給 doc 的排名

example：
  doc X 在 BM25 排名 3、在 embedding 排名 1
  RRF score = 1/(60+3) + 1/(60+1) = 0.0159 + 0.0164 = 0.0323

按 RRF score 排序、取 top-K
```

優點：不需要 normalize 不同 retriever 的分數、簡單可靠
缺點：不能 fine-tune 兩條路線的權重

### Weighted score fusion

對每條路線的 score 加權平均：

```text
score = α × BM25_score_normalized + (1-α) × embedding_score_normalized
```

優點：可以調 α 偏 BM25 或 embedding
缺點：要 normalize 兩個 score scale、調 α 是 hyper-parameter

## 設計責任

讀 RAG production / retrieval framework 看到「hybrid search」「BM25 + dense」「RRF」就是這 framing。寫 code 場景的判讀：

1. **何時值得加 hybrid**：embedding-only retrieval 漏精確 keyword / 識別碼、BM25-only 漏語意相似、混合補完
2. **何時不需要**：純語意任務（embedding 已準）、純 keyword 任務（BM25 已準）、極小語料
3. **跟 [reranker](/llm/knowledge-cards/reranker/) 的組合**：hybrid retrieve top-50（BM25 top-25 + embedding top-25、RRF 合併）→ reranker rerank → LLM top-5
4. **主流實作**：Elasticsearch / OpenSearch 內建、Weaviate / Qdrant / Pinecone 都支援、Postgres 用 pg_search + pgvector
5. **跟 [4.0 RAG 章節](/llm/04-applications/rag-principles/) 的關係**：本卡是定義、章節是 retrieval pipeline 設計含 hybrid 段
