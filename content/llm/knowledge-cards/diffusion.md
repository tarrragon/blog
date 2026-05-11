---
title: "Diffusion"
date: 2026-05-11
description: "產圖用的生成式 AI 架構：跟寫 code 用的 Transformer 是不同路線"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Diffusion 的核心概念是「從純雜訊開始、逐步去噪生成完整資料的神經網路架構」。產圖（Stable Diffusion、Flux、SDXL）、產影片、產音樂多半用 Diffusion。它跟寫 code 用的 [Transformer](/llm/knowledge-cards/transformer/) 是兩個獨立的生成式 AI 路線、推論流程、工具鏈、適合任務都不同。

## 概念位置

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

## 設計責任

聽到「換 model 就能產圖」的說法時、回到本卡確認：產圖是另一個領域、要切換到 Diffusion 工具鏈、而非在 Ollama 上下載產圖模型。寫 code 工作流跟產圖工作流分開學、避免兩邊半生不熟。對 Mac 使用者來說、Draw Things（macOS 原生 app）是產圖入門的最低門檻路徑。
