---
title: "GGUF"
date: 2026-05-11
description: "llama.cpp 生態定義的模型權重格式：把權重、tokenizer、metadata 打包成單一檔案"
weight: 1
tags: ["llm", "knowledge-cards"]
---

GGUF（GGML Unified Format）的核心概念是「llama.cpp 系統定義的模型權重格式」，把模型權重、tokenizer 設定、模型 metadata 全部打包進單一檔案。Ollama 內部存的就是 GGUF，多數本地推論伺服器（除了走 [MLX](/llm/knowledge-cards/mlx/) 路線的）也支援。

## 概念位置

GGUF 屬於模型層的封裝格式，跟 Safetensors（Hugging Face 通用）、MLX format（Apple 生態）是平行的選擇。它的設計目標是「單一檔案、跨平台、支援多種[量化](/llm/knowledge-cards/quantization/)等級」。Ollama、LM Studio、llama.cpp 都用 GGUF；想跑 MLX 系統的 oMLX 則要 MLX format 權重。

## 可觀察訊號與例子

Hugging Face 上 GGUF 檔案命名通常含量化標籤：

| 檔名範例                             | 解讀                                      |
| ------------------------------------ | ----------------------------------------- |
| `gemma-4-31b-it-Q4_K_M.gguf`         | Gemma 4、31B、instruct-tuned、Q4_K_M 量化 |
| `Llama-3.3-70B-Instruct-Q5_K_M.gguf` | Llama 3.3、70B、instruct、Q5_K_M          |
| `qwen3-coder-30b-Q8_0.gguf`          | Qwen3-Coder、30B、Q8 量化                 |

社群常見的高品質 GGUF 提供者有 `bartowski`、`unsloth`、`TheBloke`（已退坑）等；挑下載量高、最近更新的 repo 較安全。

## 設計責任

直接下載 GGUF 多半用於 LM Studio 與 llama.cpp 場景。Ollama 使用者通常透過 `ollama pull` 拉模型，背後格式也是 GGUF、但細節對使用者透明。想自己量化模型（從 Safetensors 轉 GGUF）要用 llama.cpp 的 `quantize` 工具，這是少數需要直接面對 GGUF 內部的場景。
