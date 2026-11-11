---
title: "Query-Document Gap"
date: 2026-05-14
description: "使用者 query 與文件語言在詞彙、形態、抽象層級或領域分佈上的落差，是 RAG retrieval miss 的常見原因"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query-document gap 的核心概念是「**使用者 query 的語言形狀跟被檢索文件的語言形狀不一致**」。它是 [RAG](/llm/knowledge-cards/rag/) retrieval miss 的常見原因：query 可能是口語問句，document 可能是正式陳述、專業術語、程式碼符號或另一種抽象層級。

## 跟其他概念的關係

Query-document gap 位在 query 端與 embedding / search 端之間。它跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 的字面 vs 語意互補相關，也跟 [query rewriting](/llm/knowledge-cards/query-rewriting/) 與 [HyDE](/llm/knowledge-cards/hyde/) 直接相鄰：前者改寫 query，後者生成假設文件來靠近 document 分佈。

## 可觀察訊號與例子

使用者問「API 為什麼很慢」，文件寫的是「tail latency、database query plan、connection pool saturation」。兩者意思相關，但 phrasing、抽象層級與術語不同，embedding 可能命中弱，BM25 可能完全漏掉。

## 判斷條件與後果

Query-document gap 有幾種類型，各種修法縮小的是其中不同的落差：

- **落差是同義詞、口語對正式用詞、跨語言或 domain jargon 時**，[query rewriting](/llm/knowledge-cards/query-rewriting/) 把 query 改寫成文件用的詞，代價只多一次 LLM call，是成本最低的修法。
- **落差在句子形態（query 是問句，文件是陳述或程式碼）時**，改寫後的 query 仍是問句，跟文件的 embedding 分布還有距離；[HyDE](/llm/knowledge-cards/hyde/) 先生成一份假設文件再 embed，比對的兩邊都是文件的形態。
- **query 帶著識別碼或精確 keyword、同時也需要語意比對時**，只用 embedding 會漏掉要字面相同才算命中的識別碼，只用 BM25 會漏掉換了說法的文件，[hybrid search](/llm/knowledge-cards/hybrid-search/) 讓兩路一起查。
- **上面的修法讓正確文件進了 top-k、但排在最前面的仍不是它時**，剩下的落差在細粒度的匹配，bi-encoder 的分數分不出來，由 [reranker](/llm/knowledge-cards/reranker/) 用 cross-encoder 重排。
