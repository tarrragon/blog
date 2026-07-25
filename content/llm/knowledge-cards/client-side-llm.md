---
title: "Client-Side LLM / Embedding"
date: 2026-05-12
description: "在 browser 內直接跑 LLM 或 embedding model 的 paradigm、靜態網站做 RAG 的關鍵基底"
weight: 1
tags: ["llm", "knowledge-cards", "client-side", "browser", "deployment"]
---

Client-side LLM / embedding 的核心概念是「**模型權重下載到使用者瀏覽器、用 WebGPU 或 WebAssembly 直接在 browser 內推論、不經過任何 server**」。代表 runtime：WebLLM（MLC AI、用 WebGPU）、wllama（llama.cpp 的 WebAssembly port）、`@xenova/transformers`（瀏覽器版 transformers）。是「靜態網站做 [RAG](/llm/knowledge-cards/rag/)」、「離線可用 LLM 應用」這類場景的關鍵基底。

## 概念位置

跟其他 LLM deployment 形態的對比：

| 形態                                                      | 模型權重位置         | 推論執行位置   | 隱私                    | 適合                 |
| --------------------------------------------------------- | -------------------- | -------------- | ----------------------- | -------------------- |
| 雲端 LLM API                                              | 雲端伺服器           | 雲端           | 視 vendor 政策          | 高品質、production   |
| 本地 [推論伺服器](/llm/knowledge-cards/inference-server/) | 本機磁碟             | 本機 process   | 完全本地                | 寫 code、個人 dev    |
| **Client-side LLM**                                       | 使用者 browser cache | 使用者 browser | 完全本地（不經 server） | 靜態網站、demo、離線 |

主流 client-side runtime（2026/5）：

| Runtime                | 機制                                 | 模型支援                                         | 典型體積        |
| ---------------------- | ------------------------------------ | ------------------------------------------------ | --------------- |
| `@xenova/transformers` | WASM、ONNX 格式                      | sentence-transformers、小型 LLM、CLIP、embedding | < 100 MB / 模型 |
| WebLLM（MLC）          | WebGPU、自家 MLC compiled            | Llama / Qwen / Gemma / Phi 等 1-13B              | 1-8 GB / 模型   |
| wllama                 | WASM、llama.cpp 編譯版               | GGUF Q4 等量化模型、< 4B 為主                    | 0.5-4 GB / 模型 |
| `transformers.js`      | WASM、跟 `@xenova/transformers` 同源 | 同上                                             | 同上            |

## 設計責任

讀靜態網站 / 前端 RAG / 離線 LLM 教學看到「WebGPU LLM」「browser-side embedding」「offline LLM」就是這 paradigm。寫 code 場景的判讀：

1. **首訪載入慢**：browser 第一次要下載模型權重（embedding 模型 ~50MB、LLM 1-5GB）、首訪體驗差；後續訪問 cache 起來、變快
2. **WebGPU 支援度**：2026/5 仍非所有 browser / 裝置都穩定支援、Safari iOS 較弱；fallback 到 WASM 但速度降一個量級
3. **模型完整性沒簽章**：使用者下載到的模型權重沒類似 [GGUF model card](/llm/knowledge-cards/model-card/) 的官方驗證、要靠 CDN + HTTPS 信任、不像本地 Ollama 有 hash 比對
4. **適合「embedding + 小 LLM」、不適合「30B reasoning」**：browser 記憶體跟 WebGPU 算力都遠不如本地 Ollama、選 < 4B 模型較實際
5. **跟資安的關係**：client-side 不需要 server API key、隱私強；但模型分發鏈（CDN → browser）成為新的供應鏈面、見 [4.16 靜態 RAG deployment](/llm/04-applications/static-and-serverless-rag-deployment/) 的資安段
