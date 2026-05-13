---
title: "Reranker"
date: 2026-05-12
description: "對 retrieval top-K 結果用 cross-encoder 重新排序的 RAG 第二階段、品質提升顯著但 latency / cost 增加"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Reranker 的核心概念是「**對 [retrieval](/llm/knowledge-cards/rag/) 第一階段拿到的 top-K（如 50）結果、用 cross-encoder 模型重新評分、排出 top-N（如 5）給 LLM**」。是 RAG 第二階段、補 bi-encoder（[embedding model](/llm/knowledge-cards/embedding-model/)）對 query-document 細粒度匹配的不足、品質提升明顯（recall@5 通常 +10-30%）但成本 / latency 增加。

## 概念位置

Bi-encoder vs cross-encoder 的差別：

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

## 設計責任

讀 RAG / production retrieval docs 看到「reranker」「cross-encoder」「rerank stage」就是這 framing。寫 code 場景的判讀：

1. **何時值得加 reranker**：retrieval 結果有「相關但不精確」問題、top-K hit rate 高但 top-5 hit rate 低、有 latency / cost budget
2. **何時不需要**：小語料（< 1000 docs、retrieval 已準）、明確 keyword 任務（BM25 已準）、latency 敏感（< 100ms TTFT）
3. **Pipeline 設計**：bi-encoder retrieve top-50 → reranker rerank → 給 LLM top-5；50/5 是常見起點、看實測調
4. **跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 結合**：BM25 + embedding hybrid retrieve top-50 → reranker rerank → LLM、是 production RAG 標配
5. **跟 [4.1 RAG 章節](/llm/04-applications/rag-principles/) 的關係**：本卡是定義、章節是 retrieval pipeline 設計（含 reranker / hybrid 段）
