---
title: "Adaptive Retrieval"
date: 2026-05-14
description: "RAG 控制流中先判斷是否需要檢索，只在外部知識有價值時才 retrieve"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Adaptive retrieval 的核心概念是「**先判斷問題是否需要 [RAG](/llm/knowledge-cards/rag/) 外部檢索，再決定要不要 retrieve**」。它避免每個 query 都塞入外部 chunk，降低 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)，也減少無關內容干擾模型。

## 跟其他概念的關係

Adaptive retrieval 位在 [RAG](/llm/knowledge-cards/rag/) 的控制流端。它跟 [query rewriting](/llm/knowledge-cards/query-rewriting/) 不同：rewriting 假設要 retrieve，只改查詢形狀；adaptive retrieval 先決定 retrieve 是否必要。

## 可觀察訊號與例子

「2+2 等於多少」不需要 retrieve；「公司退款政策第 4 條怎麼說」需要 retrieve。若使用者 query 一半是聊天、一半是 factual lookup，adaptive retrieval 可以明顯降低 retrieval cost。

## 判斷條件與後果

判斷要不要 retrieve 的元件可以是規則、小模型、主模型的 self-report 或 confidence signal。判斷器判成不需要檢索、而模型不知道答案時，模型照樣用自己的參數知識作答，回答看起來有把握而內容是錯的；原因是過度自信的模型給出的 self-report 與 confidence 都偏高，判斷器分不出它知不知道。這種誤判在閒聊類 query 上的代價是一次較差的回答，在「公司退款政策第 4 條怎麼說」這類事實問答上是一段錯的政策內容，所以高風險的事實問答預設 retrieve，或在判成不檢索之後保留一條改走檢索的 fallback。
