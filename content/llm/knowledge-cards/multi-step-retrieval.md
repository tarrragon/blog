---
title: "Multi-Step Retrieval"
date: 2026-05-14
description: "RAG 中多輪 retrieve → 判斷 → 再 retrieve 的控制流，用來處理 multi-hop 問題"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Multi-step retrieval 的核心概念是「**讓 [RAG](/llm/knowledge-cards/rag/) retrieval 變成多輪控制流，而不是一次性取 top-k**」。模型先讀第一輪檢索結果，判斷資訊是否足夠，再決定下一個 sub-query。

## 概念位置

它是 [RAG](/llm/knowledge-cards/rag/) 與 [agent loop](/llm/knowledge-cards/agent-loop/) 的交界：控制流比 vanilla RAG 複雜，但目標仍是補齊回答所需 context，而不是任意行動。

## 可觀察訊號與例子

多 hop 問題常需要 multi-step retrieval：先查 A 的屬性，再用該屬性查 B，最後比較。單次 retrieve 可能只抓到其中一邊，導致回答缺關鍵證據。

## 設計責任

Multi-step retrieval 只有在問題確實需要多 hop、latency budget 允許、且有停止條件時才划算。沒有 stop condition 時容易無限 retrieve；沒有資訊足夠性判斷時容易多花 cost 卻沒提升。
