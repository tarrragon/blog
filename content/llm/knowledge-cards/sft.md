---
title: "SFT（Supervised Fine-Tuning）"
date: 2026-05-12
description: "在 base model 上用「指令-回答」對資料微調、讓模型會跟著指令走"
weight: 1
tags: ["llm", "knowledge-cards", "training"]
---

SFT（Supervised Fine-Tuning、指令微調）的核心概念是「在 [base model](/llm/knowledge-cards/base-model/) 上、用人類示範的『指令-回答』成對資料做監督式 fine-tune、讓模型從『接龍』變成『跟指令走』」。SFT 是 [pre-training](/llm/knowledge-cards/pre-training/) 跟 alignment（[RLHF](/llm/knowledge-cards/rlhf/) / [DPO](/llm/knowledge-cards/dpo/)）之間的橋。

## 跟其他概念的關係

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

## 判斷條件與後果

讀 model card 看到「instruct」「chat」「-it」「sft」等 suffix、就是經過 SFT 的版本。寫 code 場景用的模型幾乎都是 SFT 後的（base model 對話能力差、實用度低）。Coding-tuned 模型（如 Qwen3-Coder）是 SFT 階段大量加入 code 對話資料的特化版本、跟通用 instruct 模型在 code 任務上有可觀差距。

挑模型與自己做 SFT 時，判斷各有一個條件。挑模型時，條件是使用方式：拿來對話或下指令時，base model 會把指令當成要接下去的文字，輸出另一串類似的指令而不是答案，所以這類用途選有 instruct 或 chat 標記的版本；base model 適合的用途是拿來自己再做 SFT，原因是它還沒有被某一套指令資料定型。自己做 SFT 時，條件是資料的量與涵蓋範圍：資料量少、只涵蓋一個窄領域時，全參數 fine-tune 會讓模型在這個領域變好，同時在資料沒涵蓋的任務上退步（災難遺忘），原因是所有權重都朝這批資料移動、覆蓋了 pre-training 學到的部分；這是 [LoRA](/llm/knowledge-cards/lora/) 只訓練少量新增參數、凍結原始權重的出發點。
