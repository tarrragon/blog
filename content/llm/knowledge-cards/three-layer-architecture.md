---
title: "Three-Layer Architecture"
date: 2026-05-14
description: "把本地 LLM 工具拆成介面層、推論伺服器層、模型權重層的基礎心智模型"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "local-llm"]
---

Three-layer architecture（三層架構）的核心概念是「**把本地 LLM 系統拆成介面層、[inference server](/llm/knowledge-cards/inference-server/) 層、模型層**」。這個分層讓讀者能判斷一個工具是在處理使用者互動、模型 serving，還是權重本身。

## 概念位置

三層責任分工如下：

```text
介面層：CLI / IDE plugin / Web UI，負責接收任務與顯示結果
伺服器層：inference server，負責載入模型、提供 API、跑推論
模型層：權重檔與 tokenizer，負責提供可被執行的神經網路參數
```

它跟 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 的關係是：API 是介面層跟伺服器層之間的標準接縫；跟 [inference server](/llm/knowledge-cards/inference-server/) 的關係是：伺服器層是三層中的中介。

## 可觀察訊號與例子

看到 Continue.dev、Open WebUI、aider，通常是在介面層；看到 Ollama、LM Studio server、llama.cpp server、vLLM，通常是在伺服器層；看到 GGUF、Safetensors、MLX 權重，通常是在模型層。LM Studio 這類 all-in-one 工具會跨層，但仍可拆成 UI 與 server 兩種責任。

## 設計責任

排錯或換工具時，先問「問題出在哪一層」。連不上 `localhost` 是伺服器或網路問題；回答品質差多半是模型或 prompt 問題；IDE 操作不順是介面層問題。完整推導見 [0.2 三層架構](/llm/00-foundations/three-layer-architecture/)。
