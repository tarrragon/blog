---
title: "Adaptive Retrieval"
date: 2026-05-14
description: "RAG 控制流中先判斷是否需要檢索，只在外部知識有價值時才 retrieve"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Adaptive retrieval 的核心概念是「**先判斷問題是否需要 [RAG](/llm/knowledge-cards/rag/) 外部檢索，再決定要不要 retrieve**」。它避免每個 query 都塞入外部 chunk，降低成本，也減少無關內容干擾模型。

## 概念位置

Adaptive retrieval 位在 [RAG](/llm/knowledge-cards/rag/) 的控制流端。它跟 [query rewriting](/llm/knowledge-cards/query-rewriting/) 不同：rewriting 假設要 retrieve，只改查詢形狀；adaptive retrieval 先決定 retrieve 是否必要。

## 可觀察訊號與例子

「2+2 等於多少」不需要 retrieve；「公司退款政策第 4 條怎麼說」需要 retrieve。若使用者 query 一半是聊天、一半是 factual lookup，adaptive retrieval 可以明顯降低 retrieval cost。

## 設計責任

判斷器可以是規則、小模型、主模型 self-report 或 confidence signal。風險是模型過度自信而跳過檢索；高風險事實問答應偏向 retrieve 或提供 fallback。
