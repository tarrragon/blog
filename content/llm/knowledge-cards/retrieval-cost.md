---
title: "Retrieval Cost"
date: 2026-05-14
description: "RAG 檢索帶來的 latency、token、embedding、reranker、LLM call 與維護成本，用來判斷增強是否划算"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval", "cost"]
---

Retrieval cost 的核心概念是「**每一次 retrieve 與其周邊增強會消耗多少 latency、token、compute 與維護成本**」。它讓 [RAG](/llm/knowledge-cards/rag/) 設計從「能不能找更多資料」轉成「多找這些資料是否值得」。

## 概念位置

Retrieval cost 橫跨 query 端、retrieval 端、context 組裝端與控制流端。它跟 [TTFT](/llm/knowledge-cards/ttft/) 有關，但不只是一個延遲數字：query rewriting 多一次 LLM call，query expansion 多次 retrieve，reranker 多一段 cross-encoder 計算，retrieved chunks 進 prompt 會增加 token cost。

## 可觀察訊號與例子

常見訊號是「accuracy 有提升，但 p95 latency 變差」「每個 query 都 retrieve，聊天問題也燒 embedding / vector DB」「multi-step retrieval 連跑三輪，答案只比 single-step 好一點」。這時問題不是技術能不能做，而是收益是否大於成本。

## 設計責任

判斷 retrieval cost 要把 accuracy、latency、token budget、服務費用與維運複雜度一起看。低風險聊天可用 [adaptive retrieval](/llm/knowledge-cards/adaptive-retrieval/) 降低不必要檢索；高價值問答可接受 [reranker](/llm/knowledge-cards/reranker/) 或 [multi-step retrieval](/llm/knowledge-cards/multi-step-retrieval/) 的額外成本；即時補完則通常偏向 single-step、cache 或較小 top-k。
