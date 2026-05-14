---
title: "Query Expansion"
date: 2026-05-14
description: "RAG 檢索前把一個 query 擴成多個語意變體，增加 coverage，再合併 retrieval 結果"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query expansion 的核心概念是「**把一個使用者 query 擴成多個檢索變體，再把多路 retrieval 結果合併**」。它處理的是 query 太短、有歧義、或只覆蓋單一表述角度時的 recall 問題，跟 [query rewriting](/llm/knowledge-cards/query-rewriting/) 的單一路徑改寫不同。

## 概念位置

Query expansion 位在 [RAG](/llm/knowledge-cards/rag/) 的 query 端增強層。它會提高 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)，因為每個變體都要 retrieve；它也常跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 的 RRF 合併思路相鄰，用排名融合降低單一 query 變體失誤。

## 可觀察訊號與例子

使用者問「python deploy」時，系統可能擴成「Python application deployment」「Docker deploy Python service」「CI/CD for Python backend」。這能增加 coverage，但也可能把不同意圖混在一起。

## 設計責任

Query expansion 適合短 query、歧義 query、或同一問題有多種常見說法的場景。設計時要限制變體數量，保留 original query，並用 [retrieval recall](/llm/knowledge-cards/retrieval-recall/) 驗證是否真的提高命中率；變體太發散時應改用澄清問題或 query rewriting。
