---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards", "LLM"]
date: 2026-05-11
description: "用原子化卡片整理本地 LLM 寫 code 場景所需的概念詞彙"
weight: -1
---

前置知識卡片的目標是把本地 LLM 章節會用到的高密度術語拆成可獨立閱讀的概念。模組零的心智模型文章會引用 token、自回歸、KV cache、量化、speculative decoding、MTP、MLX、推論伺服器、OpenAI 相容 API 等詞彙；這些詞彙背後都有明確的角色、訊號與設計責任。

這個模組先建立共同語言。每張卡片只處理一個概念，並用「概念位置、可觀察訊號、接近真實的例子、設計責任」說明它在本地 LLM 生態中的角色。讀者可以從章節中遇到陌生詞時點進來補完，回到原章節仍能接續閱讀。

## 卡片分類

### 模型輸出機制

| 卡片                                                         | 核心問題                                |
| ------------------------------------------------------------ | --------------------------------------- |
| [Token](/llm/knowledge-cards/token/)                         | 模型如何把文字切成可運算單位            |
| [Autoregressive](/llm/knowledge-cards/autoregressive/)       | 模型如何一次生一個 token                |
| [Tokens Per Second](/llm/knowledge-cards/tokens-per-second/) | 生字速度如何被量化                      |
| [TTFT](/llm/knowledge-cards/ttft/)                           | 從送出 prompt 到第一個 token 的等待時間 |
| [Context Window](/llm/knowledge-cards/context-window/)       | 模型一次能處理多少 token                |
| [Prefill](/llm/knowledge-cards/prefill/)                     | prompt 首次處理時的計算階段             |
| [KV Cache](/llm/knowledge-cards/kv-cache/)                   | 已處理過的 token 如何避免重算           |

### 模型權重與量化

| 卡片                                                               | 核心問題                       |
| ------------------------------------------------------------------ | ------------------------------ |
| [Quantization](/llm/knowledge-cards/quantization/)                 | 模型權重如何用較少 bits 表示   |
| [GGUF](/llm/knowledge-cards/gguf/)                                 | llama.cpp 系統如何打包模型權重 |
| [Instruction-Tuned Model](/llm/knowledge-cards/instruction-tuned/) | 模型如何跟著 prompt 走         |
| [Base Model](/llm/knowledge-cards/base-model/)                     | 未微調的原始模型適合什麼用途   |
| [Embedding Model](/llm/knowledge-cards/embedding-model/)           | 文字如何轉成可比對的向量       |

### 推論加速技巧

| 卡片                                                               | 核心問題                          |
| ------------------------------------------------------------------ | --------------------------------- |
| [Speculative Decoding](/llm/knowledge-cards/speculative-decoding/) | 怎麼一次生多個 token              |
| [Multi-Token Prediction](/llm/knowledge-cards/mtp/)                | speculative decoding 的工程化實作 |
| [Drafter Model](/llm/knowledge-cards/drafter-model/)               | 預測未來 token 的小模型           |

### 推論基礎建設

| 卡片                                                           | 核心問題                           |
| -------------------------------------------------------------- | ---------------------------------- |
| [Inference Server](/llm/knowledge-cards/inference-server/)     | 載入模型、提供 API 的常駐 process  |
| [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) | 介面層跟伺服器層之間的標準介面     |
| [MLX](/llm/knowledge-cards/mlx/)                               | Apple Silicon 的數值運算 framework |

### 硬體與架構

| 卡片                                                                | 核心問題                             |
| ------------------------------------------------------------------- | ------------------------------------ |
| [Memory Bandwidth](/llm/knowledge-cards/memory-bandwidth/)          | 為什麼記憶體頻寬決定生字速度         |
| [Unified Memory Architecture](/llm/knowledge-cards/unified-memory/) | Apple Silicon 怎麼讓模型用滿大記憶體 |
| [Transformer](/llm/knowledge-cards/transformer/)                    | 寫 code 用的 LLM 是哪種神經網路      |
| [Diffusion](/llm/knowledge-cards/diffusion/)                        | 產圖用的是哪種神經網路               |

### 評估指標

| 卡片                                         | 核心問題                  |
| -------------------------------------------- | ------------------------- |
| [SWE-bench](/llm/knowledge-cards/swe-bench/) | coding 能力如何被量化比較 |

### 應用層模式

| 卡片                                                       | 核心問題                                       |
| ---------------------------------------------------------- | ---------------------------------------------- |
| [RAG](/llm/knowledge-cards/rag/)                           | 怎麼給 LLM 動態外掛知識                        |
| [LLM Agent](/llm/knowledge-cards/agent/)                   | 把控制流交給 LLM 的應用模式                    |
| [Function Calling](/llm/knowledge-cards/function-calling/) | 模型訓練建立的呼叫工具能力                     |
| [MCP](/llm/knowledge-cards/mcp/)                           | LLM application ↔ tool server 的標準化協議 |
| [Chunking](/llm/knowledge-cards/chunking/)                 | 把長文件切成 retrieval 片段的 resolution vs context loss 取捨 |
| [Vector Database](/llm/knowledge-cards/vector-database/)   | 高維向量儲存 + ANN 檢索、RAG production 的關鍵元件 |

### Production 推論

| 卡片                                       | 核心問題                            |
| ------------------------------------------ | ----------------------------------- |
| [Batching](/llm/knowledge-cards/batching/) | 多 request 一起跑、攤平 memory bandwidth 成本、throughput vs latency 取捨 |

## 卡片寫法

每張卡片維持四段：

1. **核心概念**：用一句話說明這個術語承擔什麼責任。
2. **概念位置**：說明它在本地 LLM 三層架構（介面 / 伺服器 / 模型）的哪一層、跟其他概念的關係。
3. **可觀察訊號與例子**：用真實使用情境說明這個概念何時會出現、會以什麼形式被讀者察覺。
4. **設計責任**：使用者或工程師遇到這個概念時要做哪些判斷或設定。

卡片之間互相連結，章節文章使用術語時優先連到卡片。卡片是概念索引，章節文章負責情境推導；兩者分工讓讀者可以快速查詢術語，也能完整跟著章節思考。

## 卡片與章節的關係

模組零的概念文章（[本地 vs 雲端](/llm/00-foundations/local-vs-cloud/)、[為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/)、[三層架構](/llm/00-foundations/three-layer-architecture/) 等）會引用大量卡片術語；模組一的實作文章（[Ollama 安裝](/llm/01-local-llm-services/ollama/)、[模型選型](/llm/01-local-llm-services/model-selection-priority/) 等）也會用到同一批詞彙。卡片讓兩個模組共用詞彙、避免各自重新定義。
