---
title: "Context Packing"
date: 2026-05-14
description: "RAG retrieve 後把 chunks 去重、排序、壓縮、標來源，再塞進 prompt 的組裝決策"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval", "context"]
---

Context packing 的核心概念是「**retrieve 拿到候選 chunks 後，決定哪些內容、以什麼順序、帶哪些 metadata 塞進 prompt**」。它是 [RAG](/llm/knowledge-cards/rag/) 在 retrieval 與 generation 之間的 context 組裝層，有別於 retrieval 本身。

## 概念位置

Context packing 位在 top-k retrieval 結果與 LLM prompt 之間。它跟 [retrieval source](/llm/knowledge-cards/retrieval-source/) 相鄰，因為來源 metadata 會影響引用；也跟 [lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 相鄰，因為 chunk 順序會影響模型注意力。

## 可觀察訊號與例子

常見 packing 決策包含 dedup 重複 chunk、把最相關內容放前後、按 document order 保留段落流、摘要或壓縮過長 chunks、在每段前加 source path 與 score。這些決策會改變答案品質、token cost 與可追溯性。

## 設計責任

設計 context packing 時要回答：哪些 chunk 真的要進 prompt、順序如何安排、是否保留來源、是否需要 summarization / compression。高追溯場景優先保留 source metadata；長 context 場景要避免把重要 chunk 放在中間；latency 敏感場景要限制 top-k 與 compression call。
