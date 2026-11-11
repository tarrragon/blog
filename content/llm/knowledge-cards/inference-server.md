---
title: "Inference Server"
date: 2026-05-11
description: "載入模型權重、處理 prompt、產生 token 的常駐 process"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Inference Server（推論伺服器）的核心概念是「常駐在機器上、載入模型權重、接收 API 請求、跑推論、回傳生成內容的 process」。本地 LLM [三層架構](/llm/knowledge-cards/three-layer-architecture/) 中、推論伺服器位於介面層（CLI / IDE / Web UI）與模型層（權重檔）之間。

## 跟其他概念的關係

推論伺服器封裝模型載入、[量化](/llm/knowledge-cards/quantization/)、[KV cache](/llm/knowledge-cards/kv-cache/) 管理、[speculative decoding](/llm/knowledge-cards/speculative-decoding/) 等推論細節、對外提供 HTTP API。多數本地推論伺服器同時提供 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 與自家原生 API。

## 可觀察訊號與例子

2026 年 5 月主流本地推論伺服器：

| 伺服器    | 預設 port | 內部引擎                         | 適合誰                  |
| --------- | --------- | -------------------------------- | ----------------------- |
| Ollama    | 11434     | llama.cpp                        | 多數使用者的預設        |
| LM Studio | 1234      | llama.cpp + GUI                  | GUI 派、探索新模型      |
| llama.cpp | 8080      | 自己                             | 進階使用者、特殊量化    |
| oMLX      | 8000      | [MLX](/llm/knowledge-cards/mlx/) | 長 context coding agent |

並存可行：port 不同就不衝突、Continue.dev 等介面層可以同時設多個 model、各指向不同伺服器。

## 判斷條件與後果

推論伺服器的三個條件各自決定一件事：是否提供 OpenAI 相容 API，決定能接哪些介面層，不提供時，只會呼叫 OpenAI API 的介面層接不上；支援哪些模型格式（[GGUF](/llm/knowledge-cards/gguf/)、MLX format），決定能載入哪些權重檔；支援哪些加速技巧（[MTP](/llm/knowledge-cards/mtp/) 等），決定同一台機器的生成速度是否還能提高。寫 code 場景的多數使用者，Ollama 已經滿足這三項的需要；其他伺服器處理的是特定需求，例如 oMLX 處理長 context 的 coding agent（上面的表）。
