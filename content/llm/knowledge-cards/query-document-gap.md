---
title: "Query-Document Gap"
date: 2026-05-14
description: "使用者 query 與文件語言在詞彙、形態、抽象層級或領域分佈上的落差，是 RAG retrieval miss 的常見原因"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query-document gap 的核心概念是「**使用者 query 的語言形狀跟被檢索文件的語言形狀不一致**」。它是 [RAG](/llm/knowledge-cards/rag/) retrieval miss 的常見原因：query 可能是口語問句，document 可能是正式陳述、專業術語、程式碼符號或另一種抽象層級。

## 概念位置

Query-document gap 位在 query 端與 embedding / search 端之間。它跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 的字面 vs 語意互補相關，也跟 [query rewriting](/llm/knowledge-cards/query-rewriting/) 與 [HyDE](/llm/knowledge-cards/hyde/) 直接相鄰：前者改寫 query，後者生成假設文件來靠近 document 分佈。

## 可觀察訊號與例子

使用者問「API 為什麼很慢」，文件寫的是「tail latency、database query plan、connection pool saturation」。兩者意思相關，但 phrasing、抽象層級與術語不同，embedding 可能命中弱，BM25 可能完全漏掉。

## 設計責任

處理 query-document gap 時先判斷落差類型：同義詞、口語 vs 正式、問句 vs 陳述、跨語言、domain jargon 或識別碼。輕量修法是 query rewriting；形態落差明顯時可用 HyDE；精確 keyword 與語意都重要時用 hybrid search；仍然 top-k 不準時再加 reranker。
