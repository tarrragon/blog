---
title: "Model Tag"
date: 2026-05-12
description: "Ollama 等推論伺服器用來定位特定模型版本的命名規則"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Model Tag 的核心概念是「推論伺服器用來定位特定模型版本的字串 key」。同一個模型家族（例如 Gemma 4）會被切出十幾個 tag、每個 tag 對應不同的參數量、訓練變體與[量化](/llm/knowledge-cards/quantization/)等級、使用者用 tag 在 CLI 或 API 中指定要載入哪一份權重。

## 跟其他概念的關係

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

## 判斷條件與後果

tag 的三個欄位各自對應一種選錯的後果。`size` 超過可用記憶體時（對照[硬體記憶體預算](/llm/00-foundations/hardware-memory-budget/)），權重放不進記憶體，其他兩個欄位選得再對也跑不起來，所以它是第一個要對上的欄位。`variant` 選到 base 時，模型只會順著 prompt 往下接龍，不照指令回答，寫 code 這類對話式的任務因此用 `instruct` 或 `coding` 變體。`quantization` 交換的是品質與記憶體：等級越低佔用越小，輸出品質也越往下掉，可選的等級取決於 `size` 放進記憶體之後還剩多少空間。完整可用 tag 在各伺服器的 model registry（Ollama 在 [ollama.com/library](https://ollama.com/library)、LM Studio 在 Discover 分頁）。
