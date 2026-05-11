---
title: "Transformer"
date: 2026-05-11
description: "寫 code 用的 LLM 神經網路架構：基於 attention 機制、自回歸生成 token"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Transformer 的核心概念是「2017 年 Google 提出、基於 self-attention 機制的神經網路架構」。寫 code 用的所有 LLM（GPT、Claude、Gemma、Llama、Qwen 系列）都是 Transformer 架構；它跟產圖用的 [Diffusion](/llm/knowledge-cards/diffusion/) 是兩個不同的生成式 AI 路線。

## 概念位置

Transformer 是模型架構層的選擇、決定底層運算方式與適合的任務類型。它擅長「序列建模」：文字、code、語音、時間序列等都能用 Transformer 處理。配 [autoregressive](/llm/knowledge-cards/autoregressive/) 生成方式跑文字、跑出來的就是 LLM。

## 可觀察訊號與例子

Transformer LLM 的共通特徵：

| 特徵     | 表現                                                                                             |
| -------- | ------------------------------------------------------------------------------------------------ |
| 生成方式 | [一個 token 接一個 token](/llm/knowledge-cards/autoregressive/)                                  |
| 量化指標 | [tokens per second](/llm/knowledge-cards/tokens-per-second/)、[TTFT](/llm/knowledge-cards/ttft/) |
| 輸入處理 | [prefill](/llm/knowledge-cards/prefill/) 階段                                                    |
| 中間結果 | [KV cache](/llm/knowledge-cards/kv-cache/)                                                       |
| 容量限制 | [context window](/llm/knowledge-cards/context-window/)                                           |

Transformer 也被用在多模態場景（vision Transformer、speech Transformer）、但寫 code 場景接觸到的都是文字 Transformer。

## 設計責任

理解「寫 code 的 LLM 是 Transformer」可以幫助判讀資訊。看到「最新 Transformer 模型」報導時、知道它跟 Diffusion 是兩個路線；想跑產圖時、知道要找 Diffusion 工具（ComfyUI、Draw Things）而非 Ollama；看到「LLM 架構創新」時、可以追問是 attention 機制改良、還是換到非 Transformer 路線（如 Mamba、RWKV 等少數實驗性架構）。
