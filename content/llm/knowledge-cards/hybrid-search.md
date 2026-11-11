---
title: "Hybrid Search"
date: 2026-05-12
description: "把字面 retrieval（BM25）跟語意 retrieval（embedding）的結果用 RRF 等方法合併、補單一路線的盲點"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Hybrid search 的核心概念是「**同時跑字面 retrieval（BM25 / tf-idf）跟語意 retrieval（embedding similarity）、用 Reciprocal Rank Fusion 等方法合併結果**」。補單一路線的盲點：BM25 抓不到語意相似（同義詞 / 不同表述）、embedding 抓不到精確 keyword（術語 / 識別碼 / 罕見 entity）。是 production [RAG](/llm/knowledge-cards/rag/) 的標配。

## 跟其他概念的關係

兩條 retrieval 路線的盲點：

| 場景                                          | BM25（字面） | Embedding（語意）          |
| --------------------------------------------- | ------------ | -------------------------- |
| Query / doc 共用 keyword                      | 強           | 強                         |
| Query 用同義詞、doc 用另一字                  | 找不到       | 命中                       |
| Query 用通俗、doc 用 jargon                   | 找不到       | 命中                       |
| 精確 keyword（如 product code、UUID、API 名） | 命中         | 可能漂掉                   |
| 罕見 entity（人名 / 地名）                    | 命中         | 弱（embedding model 不熟） |
| Embedding model 不熟的 domain                 | 命中         | 表現崩                     |

BM25 是字面比對演算法、embedding 依賴 [embedding model](/llm/knowledge-cards/embedding-model/) 產生的向量相似度、兩者失效模式互補、因此需要合併方法。

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

## 判斷條件與後果

Hybrid search 是否值得加，看查詢裡是否同時出現兩種比對失效的情形。

1. **查詢同時有精確 keyword（識別碼、product code、API 名）與換了說法的語意查詢時**，embedding-only 漏掉精確 keyword，BM25-only 漏掉同義詞與不同表述，單一路線的 recall 各缺一塊，合併兩條路線補回對方的盲點（上面的盲點表）。
2. **查詢只有其中一種時**（純語意任務 embedding 已經找得準，純 keyword 任務 BM25 已經找得準），或語料極小時，多跑一條路線增加檢索成本，換不到更多相關文件。
3. **後面接 [reranker](/llm/knowledge-cards/reranker/) 時**，hybrid 負責把候選撈齊，reranker 負責排序：例如 BM25 與 embedding 各取 top-25、RRF 合併成 top-50，reranker 重排之後取 top-5 給 LLM；reranker 只排序收到的候選，hybrid 漏掉的文件它排不回來。
4. **主流實作**：Elasticsearch / OpenSearch 內建，Weaviate / Qdrant / Pinecone 都支援，Postgres 用 pg_search 加 pgvector。

Retrieval pipeline 的完整設計（含 hybrid 那一段）在 [4.1 RAG 章節](/llm/04-applications/rag-principles/)。
