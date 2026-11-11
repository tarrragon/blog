---
title: "Query Expansion"
date: 2026-05-14
description: "RAG 檢索前把一個 query 擴成多個語意變體，增加 coverage，再合併 retrieval 結果"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Query expansion 的核心概念是「**把一個使用者 query 擴成多個檢索變體，再把多路 retrieval 結果合併**」。它處理的是 query 太短、有歧義、或只覆蓋單一表述角度時的 recall 問題，跟 [query rewriting](/llm/knowledge-cards/query-rewriting/) 的單一路徑改寫不同。

## 跟其他概念的關係

Query expansion 位在 [RAG](/llm/knowledge-cards/rag/) 的 query 端增強層。它會提高 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)，因為每個變體都要 retrieve；它也常跟 [hybrid search](/llm/knowledge-cards/hybrid-search/) 的 RRF 合併思路相鄰，用排名融合降低單一 query 變體失誤。

## 可觀察訊號與例子

使用者問「python deploy」時，系統可能擴成「Python application deployment」「Docker deploy Python service」「CI/CD for Python backend」。這能增加 coverage，但也可能把不同意圖混在一起。

## 判斷條件與後果

Query 太短、有歧義，或同一件事有多種常見說法時，單一路 query 只命中其中一種表述，這是 query expansion 換得到收益的情境。擴出的每個變體各自 retrieve 一次，所以變體數直接乘上 [retrieval cost](/llm/knowledge-cards/retrieval-cost/)。變體偏離原意時（「python deploy」擴成 Docker 部署與 CI/CD 兩種不同的意圖），合併後的結果混進別的意圖的文件，命中數變多而對題的比例下降；保留 original query 那一路，合併結果裡至少有一路對的是使用者原本的說法。擴充是否提高了命中率，要拿同一組 eval query 比對擴充前後的 [retrieval recall](/llm/knowledge-cards/retrieval-recall/) 才看得出來。變體發散到不同意圖時，歧義出在 query 本身，多加變體只擴大混入的範圍，向使用者澄清或改用單一路的 query rewriting 才縮小範圍。
