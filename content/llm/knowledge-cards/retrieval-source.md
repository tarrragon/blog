---
title: "Retrieval Source"
date: 2026-05-14
description: "RAG 從哪個 corpus、index、tool 或外部系統取回內容，決定來源可信度、freshness、權限與引用責任"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval"]
---

Retrieval source 的核心概念是「**RAG 或 agent 在 retrieve 時實際查詢的資料來源**」。它是 [RAG](/llm/knowledge-cards/rag/) pipeline 中可被檢索、可被引用、也可能被污染或過期的 corpus、index、database、file system、tool response 或第三方服務——比泛稱的 source 更具體。

## 概念位置

Retrieval source 位在 ingestion、index 與 runtime retrieval 的交界。它跟 [chunking](/llm/knowledge-cards/chunking/) 不同：chunking 決定來源如何切片，retrieval source 決定來源本身是否可信、是否新鮮、是否有權限被查、是否能被引用。

## 可觀察訊號與例子

看到「從 codebase retrieve」「從歷史客服案例庫取相似案例」「從 vector DB 查 policy」「把 filesystem search 結果塞進 prompt」就是 retrieval source 問題。不同 source 的責任不同：官方 policy 文件可引用，使用者上傳文件要標記租戶與權限，網頁內容要防 prompt injection，過期 index 要能重建。

## 設計責任

設計 retrieval source 時要同時回答四件事：資料來源是否可信、資料是否新鮮、查詢者是否有權限、LLM 回答是否能追溯。高風險來源要保留 source metadata、ingestion timestamp、tenant boundary 與引用標籤；否則 retrieval 命中正確內容，也可能把不該看的資料送進 prompt。
