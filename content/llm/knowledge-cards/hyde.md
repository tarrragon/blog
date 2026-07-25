---
title: "HyDE（Hypothetical Document Embeddings）"
date: 2026-05-14
description: "用 LLM 生成假設文件、對假文件做 embedding 去 retrieve、繞過 query-document gap 的 RAG 增強技術"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

HyDE（Hypothetical Document Embeddings、Gao et al. 2022）是 [RAG](/llm/knowledge-cards/rag/) retrieval 階段的 query 端增強技術。核心觀察：**query 跟 document 在 embedding 空間的距離往往比 document 跟 document 之間更遠**——這是典型 [query-document gap](/llm/knowledge-cards/query-document-gap/)。HyDE 的做法是先用 LLM 對 query 生成「假設的答案文件」、對假文件做 embedding 拿去 retrieve、而不是直接 embed 原 query。

## 概念位置

HyDE 三步：

```text
User query
   ↓
[Step 1] LLM 生成 hypothetical document
         (可能 hallucinate、事實正確性不重要)
   ↓
[Step 2] Embed 假文件
   ↓
[Step 3] 用假文件 embedding 去 vector DB retrieve 真文件
   ↓
真實 top-k chunks → 主 LLM 回答
```

為什麼比直接 embed query 好：假文件的 phrasing、長度、結構都更接近真文件的分佈、embedding 距離更可靠。重點是**假文件當 embedding 的代理**、不是當答案——[hallucinate](/llm/knowledge-cards/hallucination/) 出錯誤事實 OK、但語意 / 領域要落對。

## 設計責任

讀 RAG paper 或工具看到「HyDE」「hypothetical document」「query-side augmentation」就是這個機制。實作判讀：

1. **適用 phrasing 落差顯著的場景**：問句 vs 陳述、口語 vs 正式、抽象 vs 技術詞彙。HyDE 原論文跨多領域都有提升、不限技術 / 學術。
2. **失效在假文件偏離主題**：LLM hallucinate 到別領域、retrieve 拿到完全不相關的東西。緩解：生成多個假文件取平均 embedding、或用 query + 假文件兩個 embedding 合併 retrieve。
3. **Cost**：每 query 多一個 LLM call（生假文件）、latency 加 500ms-1s，屬於明顯的 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)。對 latency 敏感場景考慮 [query rewriting](/llm/knowledge-cards/query-rewriting/) 等較輕量的替代。
4. **跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 互補**：HyDE 解語意 phrasing 落差、hybrid 解語意 / 字面互補、可以同時用。

完整 RAG 檢索增強技術 landscape 見 [4.2 RAG 檢索增強](/llm/04-applications/rag-retrieval-enhancements/)。
