---
title: "Embedding Model"
date: 2026-05-11
description: "把文字轉成向量的模型：用於 codebase 索引與語意搜尋"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Embedding Model 的核心概念是「把文字轉成固定維度向量、讓相似內容在向量空間中靠近」。Continue.dev 等工具用 embedding model 把 codebase 索引成向量資料庫、再用語意相似度搜尋相關片段。

## 概念位置

Embedding model 跟 chat model 是兩種不同的模型、有各自的權重檔。Chat model 用於對話與生成、embedding model 用於 retrieval。同一個推論伺服器（如 Ollama）可以同時載入兩種模型、為不同用途服務。

## 可觀察訊號與例子

寫 code 場景常用的 embedding 模型：

| 模型                | 大小  | 用途                        |
| ------------------- | ----- | --------------------------- |
| `nomic-embed-text`  | 274MB | 英文為主、Continue.dev 預設 |
| `mxbai-embed-large` | 670MB | 較強的英文 embedding        |
| `bge-m3`            | 1.2GB | 多語言（含中文）embedding   |

向量維度通常 384 ~ 1024、不同模型不同；切換 embedding 模型要重建索引、向量空間互不相容。

## 設計責任

Continue.dev 的 `@codebase` 命令依賴 embedding 模型；要先 `ollama pull nomic-embed-text` 並在 config.json 設 `embeddingsProvider`。Embedding 模型對 codebase 搜尋品質有影響、但邊際效益遠小於 chat model；先用預設 `nomic-embed-text`、需求出現再換更大模型。
