---
title: "Drafter Model"
date: 2026-05-11
description: "speculative decoding 中用來快速猜未來 token 的小模型"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Drafter Model 的核心概念是「[speculative decoding](/llm/knowledge-cards/speculative-decoding/) 中用來快速預測未來幾個 [token](/llm/knowledge-cards/token/) 的小模型」。它跑得比 target model 快很多倍、每次跑一個 forward pass 猜 N 個 token、再交給 target model 並行驗證。

## 概念位置

Drafter 與 target 形成一對：drafter 快但較不準、target 慢但準確、兩者組合得到「跑得快的近似 target」。drafter 在記憶體中跟 target 一起載入、佔額外記憶體。Gemma 4 31B + 官方 drafter 的記憶體佔用約「target 18GB + drafter 1GB」、需要 32GB+ Mac 才順暢。

## 可觀察訊號與例子

匹配的 drafter / target 對：

| Target          | Drafter        | 來源                     |
| --------------- | -------------- | ------------------------ |
| Gemma 4 31B     | Gemma 4 E4B    | Google 官方釋出          |
| Llama 3.3 70B   | Llama 3.2 1B   | 社群配對                 |
| Qwen3-Coder 30B | （尚未有官方） | Alibaba 還未釋出 drafter |

關鍵限制：drafter 與 target 必須用相同 tokenizer。Gemma 系列只能配 Gemma 系列、Llama 系列只能配 Llama 系列、跨家族沒有相容性。LM Studio 的 UI 在挑 drafter 時會自動過濾相容候選。

## 設計責任

寫 code 場景的多數使用者透過預先打包的 model tag（如 Ollama 的 [MTP](/llm/knowledge-cards/mtp/) 版本）取得 drafter、不用自己配對。想用其他模型的 speculative decoding 時、要確認社群是否有匹配的 drafter；找不到的情況下、預設用沒 speculative decoding 的版本是合理選擇、加速收益跟「找 drafter、自己配置」的成本比起來通常不划算。
