---
title: "Model Tag"
date: 2026-05-12
description: "Ollama 等推論伺服器用來定位特定模型版本的命名規則"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Model Tag 的核心概念是「推論伺服器用來定位特定模型版本的字串 key」。同一個模型家族（例如 Gemma 4）會被切出十幾個 tag、每個 tag 對應不同的參數量、訓練變體與[量化](/llm/knowledge-cards/quantization/)等級、使用者用 tag 在 CLI 或 API 中指定要載入哪一份權重。

## 概念位置

Model tag 是介面層跟[推論伺服器](/llm/knowledge-cards/inference-server/)之間的識別碼、形式由各個伺服器各自定義。Ollama 用 `family:size-variant-quantization` 的單行字串、LM Studio 用 Hugging Face 完整檔名、llama.cpp 直接用 `.gguf` 檔路徑。同一份模型權重在不同伺服器有不同 tag 字串、但指向的底層[GGUF](/llm/knowledge-cards/gguf/)權重可以是同一份。

## 可觀察訊號與例子

Ollama 的 tag 結構：

| 範例                           | 拆解                                                                   |
| ------------------------------ | ---------------------------------------------------------------------- |
| `gemma4:e4b`                   | Gemma 4、E4B（edge dense）、預設量化                                   |
| `gemma4:31b-instruct-q5_K_M`   | Gemma 4、31B、instruct-tuned、Q5_K_M 量化                              |
| `gemma4:31b-coding-mtp-bf16`   | Gemma 4、31B、coding 特化、含 [MTP](/llm/knowledge-cards/mtp/) drafter |
| `qwen3-coder:30b`              | Qwen3-Coder、30B 參數、預設量化                                        |
| `llama3.3:70b-instruct-q4_K_M` | Llama 3.3、70B、instruct、Q4_K_M                                       |

四個欄位裡、`size` 直接決定記憶體佔用、`variant`（instruct / coding / base）決定模型適合的任務型態、`quantization` 影響品質跟記憶體取捨。Tag 中省略某些欄位時、伺服器用該欄位的預設值（通常是「常用組合」）。

## 設計責任

選 tag 時要看三件事：先看 `size` 確認模型塞得進記憶體（對照[硬體記憶體預算](/llm/00-foundations/hardware-memory-budget/)）、再看 `variant` 確認用途匹配（寫 code 要選 `instruct` / `coding` 變體、避免 base model 的隨機接龍行為）、最後看 `quantization` 決定品質 / 記憶體甜蜜點。完整可用 tag 在各伺服器的 model registry（Ollama 在 [ollama.com/library](https://ollama.com/library)、LM Studio 在 Discover 分頁）。
