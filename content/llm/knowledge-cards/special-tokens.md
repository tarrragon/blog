---
title: "Special Tokens"
date: 2026-05-12
description: "在 vocab 中保留給特殊用途的 token：sequence 邊界、角色標記、padding、tool call 等"
weight: 1
tags: ["llm", "knowledge-cards", "tokenization"]
---

Special tokens（特殊 token）的核心概念是「**在 [vocab](/llm/knowledge-cards/vocabulary-size/) 中保留給控制 / 邊界 / 結構用途的 token**」、不是正常字面意義的詞。常見如 `<bos>`（begin of sequence）、`<eos>`（end of sequence）、`<pad>`（padding）、`<|user|>`、`<|assistant|>`、`<|tool_call|>` 等。

## 跟其他概念的關係

LLM 中 special tokens 的常見類型：

| Token                                     | 用途                                                            | 範例                              |
| ----------------------------------------- | --------------------------------------------------------------- | --------------------------------- |
| `<bos>` / `<s>`                           | 序列開頭                                                        | Llama、Mistral                    |
| `<eos>` / `</s>`                          | 序列結尾、模型輸出這個就停                                      | 所有 LLM                          |
| `<pad>`                                   | 把 batch 內不同長度 sequence 填齊                               | 訓練 / batched 推論時用           |
| `<unk>`                                   | 遇到 vocab 外的 token（byte-level BPE 已不需要）                | 早期 tokenizer                    |
| `<\|user\|>` / `<\|assistant\|>`          | Chat template 角色標記                                          | Llama 3 chat、Qwen chat           |
| `<\|im_start\|>` / `<\|im_end\|>`         | ChatML 格式的對話邊界                                           | OpenAI、Qwen 系列                 |
| `<\|tool_call\|>` / `<\|tool_response\|>` | Tool use / function calling 訊號                                | Llama 3.1+ 等支援 tool use 的模型 |
| `<think>` / `</think>`                    | [Chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 標記 | DeepSeek-R1、O1 風格模型          |

關鍵特性：

1. **訓練時用特殊 token ID 標記**：模型透過大量範例學會「看到 `<\|user\|>` 後面是使用者輸入、看到 `<\|assistant\|>` 後面要生成回答」。
2. **Chat template 把這些組合起來**：把使用者輸入 + 系統 prompt + 對話歷史依特定格式插入這些 token、組成模型訓練時看過的格式。
3. **`<eos>` 的 sampling 行為**：模型輸出 `<eos>` 後、推論伺服器停止生成、所以「為什麼回答突然停了」很多時候就是模型決定發 EOS。

## 判斷條件與後果

Special tokens 的排列由 chat template 決定（`tokenizer_config.json` 裡的 `bos_token`、`eos_token`、`chat_template` 就是這組設定），模型看到訓練時見過的格式，才會照預期分辨角色、找到回答的起點。透過 Continue.dev 或 Ollama 呼叫模型時，伺服器自動套用模型的 chat template，使用者輸入被轉成正確的 special token 格式。自己寫 inference code 而手動拼字串時，少了一個角色標記或套了別的模型的格式，模型分不出哪一段是使用者輸入、從哪裡開始回答，輸出可能接著續寫 prompt、遲遲不發 `<eos>` 或格式錯亂；`tokenizer.apply_chat_template()` 讀的是模型自己的 template，用它組 prompt，格式就跟訓練時一致。
