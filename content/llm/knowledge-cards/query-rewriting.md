---
title: "Query Rewriting"
date: 2026-05-14
description: "在 RAG 檢索前改寫使用者查詢，讓 query 更接近文件語言與索引分佈"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query rewriting 的核心概念是「**在 [RAG](/llm/knowledge-cards/rag/) retrieval 前把使用者 query 改寫成更適合搜尋的形狀**」。使用者常用口語、模糊或情境化說法，文件則使用正式術語；改寫能縮小 [query-document gap](/llm/knowledge-cards/query-document-gap/)。

## 跟其他概念的關係

Query rewriting 位在 [RAG](/llm/knowledge-cards/rag/) pipeline 的 query 端，早於 embedding、hybrid search、reranker 與 [context packing](/llm/knowledge-cards/context-packing/)。它跟 HyDE 不同：rewriting 產生更好的查詢句，HyDE 產生假設文件再拿去 embed。

## 可觀察訊號與例子

使用者問「API 為什麼很慢」，rewriting 可能改成「API latency bottleneck, tail latency, database query optimization」。這能讓 retrieval 更容易命中正式文件中的用詞，但會增加 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)。

## 判斷條件與後果

改寫後的查詢偏離原始意圖時（把「診斷原因」改成「優化方案」），retrieve 回來的文件對的是改寫後的題目，回答看起來完整而答非所問，原因是 retriever 只看得到改寫後的文字；所以 original query 要留著，retrieve 之後拿它檢查結果是否對題。
