---
title: "Diffusion"
date: 2026-05-11
description: "產圖用的生成式 AI 架構：跟寫 code 用的 Transformer 是不同路線"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Diffusion 的核心概念是「從純雜訊開始、逐步去噪生成完整資料的神經網路架構」。產圖（Stable Diffusion、Flux、SDXL）、產影片、產音樂多半用 Diffusion。它跟寫 code 用的 [Transformer](/llm/knowledge-cards/transformer/) 是兩個獨立的生成式 AI 路線、推論流程、工具鏈、適合任務都不同。

## 跟其他概念的關係

Diffusion 模型一次處理整張圖、用「去噪 N 步」的方式生成；跟 Transformer 的「一個 [token](/llm/knowledge-cards/token/) 接一個 token」生成方式根本不同。記憶體需求、硬體最適規格、生態系都是平行宇宙。

## 可觀察訊號與例子

Diffusion 跟 Transformer 工具鏈完全不通用：

| 維度        | Transformer LLM                         | Diffusion                                      |
| ----------- | --------------------------------------- | ---------------------------------------------- |
| 主流模型    | Gemma 4、Qwen3、Llama 3.3、GPT-5        | Stable Diffusion、Flux、SDXL                   |
| 推論伺服器  | Ollama、LM Studio、llama.cpp、oMLX      | ComfyUI、Draw Things、AUTOMATIC1111、Diffusers |
| 推論時間    | 每秒幾十 tok（autoregressive）          | 整張圖 15 ~ 60 秒（一次到位）                  |
| 硬體最適    | 記憶體大、頻寬高                        | GPU 算力高、VRAM 頻寬高                        |
| Prompt 風格 | instruction 形式                        | descriptive + negative prompt                  |
| 量化技術    | [GGUF](/llm/knowledge-cards/gguf/)、MLX | 各家不同、Diffusers 為主                       |

## 判斷條件與後果

「換 model 就能產圖」這個說法成立的前提，是產圖模型與寫 code 的模型共用同一套工具鏈；上表列的推論伺服器、量化格式與 prompt 寫法兩邊都不同，所以產圖要換成 ComfyUI、Draw Things 這類 Diffusion 工具鏈，不是在 Ollama 上多下載一個模型。兩套工具鏈的知識幾乎不互通，寫 code 的工作流與產圖的工作流可以各自獨立學，學其中一套時不必先懂另一套。Mac 使用者要入門產圖時，Draw Things 是 macOS 原生 app，不必自己架推論環境，是門檻最低的起點。
