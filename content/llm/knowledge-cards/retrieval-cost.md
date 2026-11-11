---
title: "Retrieval Cost"
date: 2026-05-14
description: "RAG 檢索帶來的 latency、token、embedding、reranker、LLM call 與維護成本，用來判斷增強是否划算"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval", "cost"]
---

Retrieval cost 的核心概念是「**每一次 retrieve 與其周邊增強會消耗多少 latency、token、compute 與維護成本**」。它讓 [RAG](/llm/knowledge-cards/rag/) 設計從「能不能找更多資料」轉成「多找這些資料是否值得」。

## 跟其他概念的關係

Retrieval cost 橫跨 query 端、retrieval 端、context 組裝端與控制流端。它跟 [TTFT](/llm/knowledge-cards/ttft/) 有關，但不只是一個延遲數字：query rewriting 多一次 LLM call，query expansion 多次 retrieve，reranker 多一段 cross-encoder 計算，retrieved chunks 進 prompt 會增加 token cost。

## 可觀察訊號與例子

常見訊號是「accuracy 有提升，但 p95 latency 變差」「每個 query 都 retrieve，聊天問題也燒 embedding / vector DB」「multi-step retrieval 連跑三輪，答案只比 single-step 好一點」。這時問題在於收益是否大於成本，而非技術能不能做。

## 判斷條件與後果

一筆 retrieval cost 是否值得付，取決於答錯的代價，跟多付的 latency、token、服務費用與維運複雜度相比哪一邊大，所以同一個增強手段在不同場景得到不同的判斷。低風險的聊天裡多數訊息不需要外部知識，每一則都 retrieve 就每一則都付 embedding 與 vector DB 的成本，答案卻沒有變好，[adaptive retrieval](/llm/knowledge-cards/adaptive-retrieval/) 只在需要時才查。高價值的問答答錯的代價高，[reranker](/llm/knowledge-cards/reranker/) 或 [multi-step retrieval](/llm/knowledge-cards/multi-step-retrieval/) 多付的計算換來的準確率值得。即時補完對延遲敏感，每多一段檢索都直接加進使用者等待的時間，所以通常停在 single-step、cache 或較小的 top-k。
