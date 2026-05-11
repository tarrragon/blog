---
title: "Multi-Token Prediction (MTP)"
date: 2026-05-11
description: "Google 為 Gemma 系列釋出的 speculative decoding 工程化實作"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Multi-Token Prediction（MTP）的核心概念是「[speculative decoding](/llm/knowledge-cards/speculative-decoding/) 的工程化實作」，特指 Google 為 Gemma 4 釋出的官方版本。它包含預訓練好的 [drafter](/llm/knowledge-cards/drafter-model/)、target 模型整合、以及優化過的推論流程。

## 概念位置

MTP 屬於模型推論優化層、跟 [autoregressive](/llm/knowledge-cards/autoregressive/) 基底並列。它是技巧、不是模型架構、也不是 framework；任何推論伺服器都可以選擇實作或忽略 MTP、模型可以選擇有沒有官方 drafter。三件事彼此獨立。

## 可觀察訊號與例子

2026 年 5 月 MTP 在各推論伺服器的支援狀態：

| 伺服器    | Gemma 4 MTP 支援                                                                |
| --------- | ------------------------------------------------------------------------------- |
| Ollama    | v0.23.1（2026/5/7）一鍵支援                                                     |
| LM Studio | 支援、需手動配置 draft model                                                    |
| llama.cpp | speculative decoding 框架在 beta、Gemma 4 官方 drafter 整合仍是 feature request |
| oMLX      | 支援                                                                            |

啟用 MTP 的速度收益主要在寫 code 場景。Google 官方數據 coding 任務 2 ~ 3 倍加速；純文字寫作、創意任務的加速幅度約 1.5 ~ 2 倍、因為 pattern 預測度較低。

## 設計責任

寫 code 場景的多數使用者透過 Ollama 一行啟用 MTP：`ollama run gemma4:31b-coding-mtp-bf16`。看到「N 倍加速」報導時要追問來源與任務：官方 Google 數據是 2 ~ 3 倍；「40%」這類數字常常來源不明、可能是社群文章作者的估算。判讀加速幅度時、回到[本卡](/llm/knowledge-cards/mtp/) 與 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 的官方來源比對。
