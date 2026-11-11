---
title: "Query Decomposition"
date: 2026-05-14
description: "把複合 query 拆成可獨立檢索的子 query，平行取得證據後再合成答案"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query decomposition 的核心概念是「**把一個複合問題拆成多個可獨立 retrieve 的子問題**」。它處理的是 [RAG](/llm/knowledge-cards/rag/) 場景中、單一 query 同時要求比較、列舉、跨 entity 查證或多維度分析時，單次 retrieval 容易只命中其中一部分的問題。

## 跟其他概念的關係

Query decomposition 位在 [RAG](/llm/knowledge-cards/rag/) 的 query 端，跟 [multi-step retrieval](/llm/knowledge-cards/multi-step-retrieval/) 相鄰但不相同。Decomposition 是先拆好 N 個子 query 平行 retrieve；multi-step retrieval 是 retrieve 後讀結果，再決定下一步要查什麼。

## 可觀察訊號與例子

「比較 A 與 B 在安全性和成本上的差異」可以拆成「A 的安全性」「B 的安全性」「A 的成本」「B 的成本」。每個子 query 都能獨立命中文件，最後再合成比較表。

## 判斷條件與後果

子問題彼此獨立，也就是每個子 query 不靠其他子 query 的結果就寫得出來，是 query decomposition 能平行 retrieve 的前提。後一個子 query 需要前一個的結果才寫得出來時（先查出某個服務用哪個資料庫，才查得到那個資料庫的備份策略），事先拆好的子 query 缺了那個還不知道的值，retrieve 回來的是泛泛的結果；這種依賴由 [multi-step retrieval](/llm/knowledge-cards/multi-step-retrieval/) 處理，它讀完上一輪的結果才決定下一個 query。子問題獨立而數量多時，每個子 query 各付一次 retrieve 的 latency 與費用，總成本隨子 query 數成長，拆解換到的命中率是否值得，拿 [retrieval cost](/llm/knowledge-cards/retrieval-cost/) 與 latency budget 比較。
