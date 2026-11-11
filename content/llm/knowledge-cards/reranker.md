---
title: "Reranker"
date: 2026-05-12
description: "對 retrieval top-K 結果用 cross-encoder 重新排序的 RAG 第二階段、品質提升顯著但 latency / cost 增加"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Reranker 的核心概念是「**對 [retrieval](/llm/knowledge-cards/rag/) 第一階段拿到的 top-K（如 50）結果、用 cross-encoder 模型重新評分、排出 top-N（如 5）給 LLM**」。是 RAG 第二階段、補 bi-encoder（[embedding model](/llm/knowledge-cards/embedding-model/)）對 [query-document gap](/llm/knowledge-cards/query-document-gap/) 的細粒度匹配不足、品質提升明顯（recall@5 通常 +10-30%）但成本 / latency 增加。

## 跟其他概念的關係

Bi-encoder（[embedding model](/llm/knowledge-cards/embedding-model/)）vs cross-encoder 的差別：

```text
Bi-encoder（embedding model、retrieval 第一階段）：
  query → embedding A
  document → embedding B（pre-compute、存 vector DB）
  score = cosine(A, B)
  → 快、可 pre-compute、適合海量 retrieval

Cross-encoder（reranker、retrieval 第二階段）：
  (query, document) 一起進模型 → 直接輸出 relevance score
  → 慢（每對都要 forward pass）、不可 pre-compute、適合 top-K rerank
```

主流 reranker：

| Reranker                           | 類型             | 適合場景                 |
| ---------------------------------- | ---------------- | ------------------------ |
| Cohere Rerank 3                    | SaaS API         | Production 高品質、多語  |
| Jina Reranker v2                   | 開源             | 開源、多語               |
| BGE Reranker（bge-reranker-v2-m3） | 開源             | 開源中文友善             |
| Voyage rerank-2                    | SaaS API         | 跟 voyage embedding 配對 |
| ColBERT v2                         | Late interaction | 介於 bi 跟 cross encoder |

## 判斷條件與後果

Reranker 對每一對 query 與文件各跑一次 cross-encoder 的 forward pass，所以是否加它，看第一階段的排序誤差有多大，以及 latency 預算還剩多少。

**值得加的情形**：top-K（例如 top-50）的 hit rate 高、top-5 的 hit rate 低，代表正確文件已經被取回、只是排得不夠前面，結果呈現「相關但不精確」。bi-encoder 把 query 與文件分開 embed，分不出這種細粒度的差別，cross-encoder 把兩者一起讀，補的正是這一段。latency 與 cost 的預算容得下多一段計算時，常見的組合是 bi-encoder（或 BM25 加 embedding 的 [hybrid search](/llm/knowledge-cards/hybrid-search/)）取回 top-50，reranker 重排後給 LLM top-5；50 與 5 是起點，依實測的命中率與延遲調整。

**不值得加的情形**：語料小（少於 1000 份文件）而 retrieval 已經準確，或任務是明確的 keyword 比對而 BM25 已經準確，這兩種的 top-5 已經包含正確文件，reranker 只增加延遲；TTFT 要求在 100ms 以下時，多一段 cross-encoder 的計算可能就超出預算。

本卡是定義，retrieval pipeline 的設計（含 reranker 與 hybrid 段）在 [4.1 RAG 章節](/llm/04-applications/rag-principles/)。
