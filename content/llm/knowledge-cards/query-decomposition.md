---
title: "Query Decomposition"
date: 2026-05-14
description: "把複合 query 拆成可獨立檢索的子 query，平行取得證據後再合成答案"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query decomposition 的核心概念是「**把一個複合問題拆成多個可獨立 retrieve 的子問題**」。它處理的是單一 query 同時要求比較、列舉、跨 entity 查證或多維度分析時，單次 retrieval 容易只命中其中一部分的問題。

## 概念位置

Query decomposition 位在 [RAG](/llm/knowledge-cards/rag/) 的 query 端，跟 [multi-step retrieval](/llm/knowledge-cards/multi-step-retrieval/) 相鄰但不相同。Decomposition 是先拆好 N 個子 query 平行 retrieve；multi-step retrieval 是 retrieve 後讀結果，再決定下一步要查什麼。

## 可觀察訊號與例子

「比較 A 與 B 在安全性和成本上的差異」可以拆成「A 的安全性」「B 的安全性」「A 的成本」「B 的成本」。每個子 query 都能獨立命中文件，最後再合成比較表。

## 設計責任

Query decomposition 適合子問題彼此獨立的複合問題。若後一個子 query 需要前一輪結果才能產生，改用 multi-step retrieval；若拆解後子 query 過多，要回到 [retrieval cost](/llm/knowledge-cards/retrieval-cost/) 與 latency budget 評估。
