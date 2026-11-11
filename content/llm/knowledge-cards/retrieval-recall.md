---
title: "Retrieval Recall"
date: 2026-05-14
description: "衡量 RAG 檢索是否把應該命中的文件或 chunk 放進 top-k 結果，是 component-level eval 的核心指標"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval", "eval"]
---

Retrieval recall 的核心概念是「**正確文件或 chunk 是否出現在 retrieval top-k 結果中**」。它把 [RAG](/llm/knowledge-cards/rag/) 的 retrieval 階段從主觀感覺改成 component-level eval，讓 generation 失敗與 retrieval miss 能分開判讀。

## 跟其他概念的關係

Retrieval recall 位在 retrieval component eval 層。它跟 [reranker](/llm/knowledge-cards/reranker/) 相鄰，因為 reranker 常用來提升 top-k 的排序品質；也跟 [query-document gap](/llm/knowledge-cards/query-document-gap/) 相鄰，因為 gap 太大會讓 expected doc 不進 top-k。

## 可觀察訊號與例子

一組 eval query 事先標出 expected chunk。若 expected chunk 出現在 top-5，記為 hit@5；一百題中 82 題命中，hit_rate@5 是 82%。若 retrieval recall 高但答案錯，問題多半在 generation 或 context packing；若 retrieval recall 低，先修 chunking、embedding、hybrid search 或 query 端增強。

## 判斷條件與後果

只看 end-to-end answer correctness 時，答錯的成因混在同一個數字裡：retrieval 沒取回正確文件、LLM 拿到正確 context 仍然 hallucination、judge 判分偏差、prompt 的寫法，在這個指標上都只是一題「答錯」，retrieval miss 因此被其他成因蓋過。retrieval recall eval 逐題存下 query、expected source、top-k 結果、score 與失敗分類，這幾種成因才分得開：expected source 不在 top-k 裡是 retrieval miss；在 top-k 裡而答案仍錯，原因在 generation 或 context packing。
