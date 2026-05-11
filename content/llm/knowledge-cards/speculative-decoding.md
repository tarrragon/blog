---
title: "Speculative Decoding"
date: 2026-05-11
description: "用小模型猜未來 token、大模型並行驗證的加速技巧"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Speculative Decoding（推測解碼）的核心概念是「用一個快的小模型（drafter）先猜未來 N 個 [token](/llm/knowledge-cards/token/)、再讓大模型（target）一次並行驗證」。大模型認同的前綴保留下來、不認同的位置之後重新生成。實際效果是「一次 forward pass 產出多個 token」、攻擊的是 [autoregressive](/llm/knowledge-cards/autoregressive/) 的單 token 瓶頸。

## 概念位置

Speculative decoding 是純加速技巧、不改變輸出品質。大模型驗證階段的數學保證：drafter 猜對時保留、猜錯時 target 自己決定下一個 token、最終結果跟「不用 drafter 直接生成」一致。它能加速的關鍵是「驗證可以並行」—— 大模型一次跑 forward pass 驗證 N 個 token 的時間、跟驗證 1 個 token 接近、因為瓶頸是 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 而非算力。

## 可觀察訊號與例子

寫 code 場景的 speculative decoding 接受率特別高，因為 code 有大量可預測 pattern（縮排、括號、import 語句、常見變數名）。drafter 猜對的機率高、整體加速明顯。

Google 為 Gemma 4 釋出官方 [drafter](/llm/knowledge-cards/drafter-model/) 後、官方數據 coding 任務 2 ~ 3 倍加速、其他任務 1.5 ~ 2 倍。

實作層面、Ollama v0.23.1（2026/5/7）一鍵啟用 `gemma4:31b-coding-mtp-bf16`、LM Studio 提供 UI 設定面板、llama.cpp 的 `--draft-model` 參數仍 beta。

## 設計責任

啟用 speculative decoding 需要 target 模型與 drafter 模型用相同 tokenizer。Gemma 4 31B 配 Gemma 4 E4B 可以工作、跨家族（Gemma 配 Llama 等）沒有相容性。多數使用者透過預先打包好的 model tag（如 Ollama 的 MTP 版本）一行啟用、無需自己挑 drafter。
