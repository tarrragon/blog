---
title: "Word2Vec"
date: 2026-05-14
description: "早期靜態詞向量方法，用 skip-gram / CBOW 從上下文學出詞語 embedding"
weight: 1
tags: ["llm", "knowledge-cards", "embedding"]
---

Word2Vec 的核心概念是「**用上下文預測任務學出靜態詞向量**」。它讓語意相近的詞在向量空間中靠近，是理解 [embedding model](/llm/knowledge-cards/embedding-model/) 與 embedding space 的經典起點。

## 概念位置

Word2Vec 屬於 LLM 前一代的 static embedding 方法，常見訓練方式是 skip-gram 與 CBOW。它跟現代 [embedding model](/llm/knowledge-cards/embedding-model/) 的差異是：Word2Vec 對同一個詞給固定向量，現代 Transformer 會依上下文產生 contextual representation。

## 可觀察訊號與例子

經典例子是 `king - man + woman ≈ queen` 這類向量類比。它展示 embedding space 可以承載語意方向，但也暴露靜態詞向量對多義詞與上下文的限制。

## 設計責任

讀 embedding 章節看到 Word2Vec 時，把它當成「embedding 概念的歷史基線」。實務 RAG 選型通常看現代 embedding model 與 [MTEB](/llm/knowledge-cards/mteb-benchmark/)，不是直接使用 Word2Vec。
