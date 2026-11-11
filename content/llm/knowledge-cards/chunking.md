---
title: "Chunking"
date: 2026-05-12
description: "把長文件切成可檢索片段的設計決策：resolution vs context loss 的本質取捨"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Chunking 的核心概念是「把長文件切成可被 retrieval 系統獨立檢索的片段」。是 [RAG](/llm/knowledge-cards/rag/) 系統的關鍵設計決策——chunk 太小、retrieval 拿到的 fragment 缺脈絡；太大、retrieval 精確度低且浪費 [context window](/llm/knowledge-cards/context-window/)。「resolution vs context loss」是無法兩全的設計取捨。

## 跟其他概念的關係

Chunking 介於 corpus 跟 [embedding model](/llm/knowledge-cards/embedding-model/) 之間、決定 embedding 的單位。同一份 corpus 不同 chunking 策略產出不同 index、retrieval 行為完全不同。Chunk 邊界也決定 retrieval 命中後給 LLM 的 context 邊界——chunk 邊界穿過語意單位、會把連貫資訊切散。

## 可觀察訊號與例子

| Chunk 大小 | 典型 token 數 | 適合場景               |
| ---------- | ------------- | ---------------------- |
| 細粒度     | 100-300       | 精確問答（單句答案）   |
| 中粒度     | 400-800       | 一般 RAG 主流          |
| 粗粒度     | 1500-3000     | 摘要任務、需要長段脈絡 |

切法策略：

- **固定 token 數**：簡單但易切過句子 / 段落中間。
- **段落感知**：用空白行切、保留段落完整。
- **語意 chunking**：用 LLM / embedding 找語意邊界。
- **結構化文件**：按 heading / section 切（markdown、code）。

跨 chunk 重複（overlap）：相鄰 chunk 留 10-20% 重疊、避免邊界訊號丟失。

## 判斷條件與後果

Chunk 的大小與切法取決於四個條件，判錯任何一個，retrieval 的結果都會變差：

1. **任務類型**：精確問答的答案在單句裡，chunk 太大時答案句被周圍文字稀釋，檢索精確度下降；摘要任務需要長段脈絡，chunk 太小時拿到的片段缺前後文。所以任務類型決定 chunk 大小的起點（上表的三種粒度）。
2. **文件結構**：markdown 與 code 有 heading、section、function 這類現成的邊界，用固定 token 數切會穿過這些邊界，把連貫的資訊切散；純文字沒有這類標記，才需要段落感知或語意 chunking 找邊界。
3. **語言混合**：中文與英文每個字元對應的 token 數不同，用字元數估 chunk 大小的 heuristic 在混合語料上會偏離實際的 token 數。
4. **Embedding model 的能力**：chunk 太短時 embedding 拿不到足夠的語意，太長時超出模型處理得好的長度，兩端都會降低 embedding 品質。

寫 code 場景的實作範例見 [RAG demo hands-on](/llm/01-local-llm-services/hands-on/rag-demo/) 的 `slice_markdown` function、設計取捨展開見 [4.1 RAG 原理](/llm/04-applications/rag-principles/) 的「Chunking 的本質取捨」段。
