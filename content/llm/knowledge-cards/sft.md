---
title: "SFT（Supervised Fine-Tuning）"
date: 2026-05-12
description: "在 base model 上用「指令-回答」對資料微調、讓模型會跟著指令走"
weight: 1
tags: ["llm", "knowledge-cards", "training"]
---

SFT（Supervised Fine-Tuning、指令微調）的核心概念是「在 [base model](/llm/knowledge-cards/base-model/) 上、用人類示範的『指令-回答』成對資料做監督式 fine-tune、讓模型從『接龍』變成『跟指令走』」。SFT 是 [pre-training](/llm/knowledge-cards/pre-training/) 跟 alignment（[RLHF](/llm/knowledge-cards/rlhf/) / [DPO](/llm/knowledge-cards/dpo/)）之間的橋。

## 概念位置

SFT 在訓練 pipeline 的位置與資料形態：

```text
資料格式（典型）：
  {"instruction": "寫一個 Python fibonacci",
   "response":    "def fib(n): ..."}

訓練：
  把 instruction + response 連起來、跑跟 pre-training 一樣的 next-token prediction
  但 loss 只算 response token 上的 cross-entropy（instruction 部分不算）
```

SFT 後同一個模型行為大改：

| 問同樣問題「寫一個 Python fibonacci」 | Base model（pre-training 後）                                                        | Instruction-tuned model（SFT 後） |
| ------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------- |
| 行為                                  | 純文字接龍：「寫一個 Python fibonacci。寫一個 JavaScript fibonacci。寫一個 Rust...」 | 直接給出 fibonacci 函式實作       |

關鍵特性：

1. **資料量遠小於 pre-training**：幾萬到幾百萬筆指令-回答對、相對 pre-training 的兆級 token 是小數字。
2. **訓練成本相對低**：通常幾百到幾千 GPU-hour、可在單機完成。
3. **容易過擬合 / 災難遺忘**：SFT 資料太少 / 太特化時、模型可能丟掉 pre-training 學到的能力、見 [LoRA](/llm/knowledge-cards/lora/) 的設計動機。

## 設計責任

讀 model card 看到「instruct」「chat」「-it」「sft」等 suffix、就是經過 SFT 的版本。寫 code 場景用的模型幾乎都是 SFT 後的（base model 對話能力差、實用度低）。Coding-tuned 模型（如 Qwen3-Coder）是 SFT 階段大量加入 code 對話資料的特化版本、跟通用 instruct 模型在 code 任務上有可觀差距。
