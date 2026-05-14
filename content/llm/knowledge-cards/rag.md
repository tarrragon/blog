---
title: "RAG"
date: 2026-05-11
description: "Retrieval-Augmented Generation：動態外掛知識給 LLM、繞開模型參數記憶的靜態限制"
weight: 1
tags: ["llm", "knowledge-cards"]
---

RAG（Retrieval-Augmented Generation）的核心概念是「給 LLM 動態外掛一份知識、在生成時從 [retrieval source](/llm/knowledge-cards/retrieval-source/) 找相關片段塞進 prompt 當 context」。它解的是 LLM 參數記憶的三個天然限制：訓練 cutoff、私有資料缺席、長尾事實壓縮損失。

## 概念位置

RAG 跟 [fine-tuning](/llm/knowledge-cards/instruction-tuned/) 跟 long context 是「讓模型知道新東西」的三條路、解的問題層次不同：RAG 動態外掛、fine-tuning 改參數、long context 直接塞 prompt。三者不互斥、常組合用。RAG 屬於應用層、依賴 [embedding model](/llm/knowledge-cards/embedding-model/) 把文字轉向量、用相似度檢索。

## 可觀察訊號與例子

寫 code 場景的典型 RAG 是 Continue.dev 的 `@codebase`：把整個 repo 切 chunk、用 [embedding model](/llm/knowledge-cards/embedding-model/) 索引成向量、query 時用 cosine similarity 找相關片段、塞進 prompt 給 LLM。判讀 RAG 結果好壞看：retrieval 片段相關性、塞進 prompt 後 LLM 是否真用上、答案是否能追溯到 source chunk，以及整段 [retrieval cost](/llm/knowledge-cards/retrieval-cost/) 是否划算。

## 設計責任

設計 RAG 系統前先評估「不做 RAG 會怎樣」：知識量小可用 long context、知識結構化可用 SQL、靜態風格特化可用 fine-tune。需要動態 + 大量 + traceable 才是 RAG 的甜蜜點。詳細展開見 [4.1 RAG 原理](/llm/04-applications/rag-principles/)。
