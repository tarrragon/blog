---
title: "Embedding Model"
date: 2026-05-11
description: "把文字轉成向量的模型：用於 codebase 索引與語意搜尋"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Embedding Model 的核心概念是「把文字轉成固定維度向量、讓相似內容在向量空間中靠近」。Continue.dev 等工具用 embedding model 把 codebase 索引成 [向量資料庫](/llm/knowledge-cards/vector-database/)、再用語意相似度搜尋相關片段。

## 跟其他概念的關係

Embedding model 跟 chat model 是兩種不同的模型、有各自的權重檔。Chat model 用於對話與生成、embedding model 用於 retrieval。同一個 [推論伺服器](/llm/knowledge-cards/inference-server/)（如 Ollama）可以同時載入兩種模型、為不同用途服務。

## 可觀察訊號與例子

寫 code 場景常用的 embedding 模型：

| 模型                | 大小  | 用途                        |
| ------------------- | ----- | --------------------------- |
| `nomic-embed-text`  | 274MB | 英文為主、Continue.dev 預設 |
| `mxbai-embed-large` | 670MB | 較強的英文 embedding        |
| `bge-m3`            | 1.2GB | 多語言（含中文）embedding   |

向量維度通常 384 ~ 1024、不同模型不同；切換 embedding 模型要重建索引、向量空間互不相容。

## 判斷條件與後果

Continue.dev 的 `@codebase` 命令查的是 embedding model 建出來的索引，所以 Ollama 上還沒有那個模型（沒有跑過 `ollama pull nomic-embed-text`）或 config.json 的 `embeddingsProvider` 沒有指到它時，`@codebase` 沒有索引可查。是否換成更大的 embedding 模型，看搜尋結果是否對題：換模型要重建整個索引，因為不同模型的向量空間互不相容，而 embedding 模型對 codebase 搜尋品質的影響，比 chat model 對回答品質的影響小得多。所以預設的 `nomic-embed-text` 搜得到相關片段時，換更大的模型付出重建索引與更多記憶體，換到的改善有限；程式碼的註解或文件是中文而搜不到相關片段時，換成 `bge-m3` 這類多語言模型才對得上這個缺口。
