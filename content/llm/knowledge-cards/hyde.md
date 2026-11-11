---
title: "HyDE（Hypothetical Document Embeddings）"
date: 2026-05-14
description: "用 LLM 生成假設文件、對假文件做 embedding 去 retrieve、繞過 query-document gap 的 RAG 增強技術"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

HyDE（Hypothetical Document Embeddings、Gao et al. 2022）是 [RAG](/llm/knowledge-cards/rag/) retrieval 階段的 query 端增強技術。核心觀察：**query 跟 document 在 embedding 空間的距離往往比 document 跟 document 之間更遠**——這是典型 [query-document gap](/llm/knowledge-cards/query-document-gap/)。HyDE 的做法是先用 LLM 對 query 生成「假設的答案文件」、對假文件做 embedding 拿去 retrieve、而不是直接 embed 原 query。

## 跟其他概念的關係

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

## 判斷條件與後果

HyDE 的判斷看三個條件：query 與文件的 phrasing 落差、假文件是否偏題，以及延遲預算。

1. **query 與文件的 phrasing 落差大時**（問句對陳述、口語對正式、抽象說法對技術詞彙），直接 embed query 得到的距離不可靠，假文件的 phrasing 接近真文件，retrieve 的結果因此改善；HyDE 原論文在多個領域都有提升，不限技術或學術語料。
2. **LLM 生成的假文件偏到別的領域時**，retrieve 回來的是那個領域的文件，跟原 query 不相關，原因是 retrieve 只看假文件的 embedding；生成多份假文件取平均 embedding，或把 query 與假文件兩個 embedding 合併 retrieve，單一份假文件偏題的影響就被稀釋。
3. **延遲預算緊時**，HyDE 每個 query 多一次 LLM 呼叫來生假文件，延遲多 500ms 到 1s，是明顯的 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)；這類場景的替代是 [query rewriting](/llm/knowledge-cards/query-rewriting/) 這類較輕量的做法。
4. **跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 一起用時**，兩者處理不同的落差：HyDE 縮小 query 與文件的 phrasing 落差，hybrid 讓字面比對與語意比對互補，所以可以疊用。

完整 RAG 檢索增強技術 landscape 見 [4.2 RAG 檢索增強](/llm/04-applications/rag-retrieval-enhancements/)。
