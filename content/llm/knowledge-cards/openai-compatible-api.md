---
title: "OpenAI-Compatible API（OpenAI 相容 API）"
date: 2026-05-11
description: "本地推論伺服器跟雲端 OpenAI 共用的 API 形狀標準"
weight: 1
tags: ["llm", "knowledge-cards"]
---

OpenAI 相容 API 的核心概念是「實作 OpenAI 在 2023 年定義的 `POST /v1/chat/completions` 介面、讓介面層工具不改一行 code 就能切換本地與雲端」。它是事實標準、後來幾乎所有本地[推論伺服器](/llm/knowledge-cards/inference-server/)都實作這份規格。

## 跟其他概念的關係

OpenAI 相容 API 是介面層與伺服器層之間的標準介面。它承諾 API 形狀（request / response schema、streaming 格式、錯誤碼）一致；對「[模型能力](/llm/knowledge-cards/capability-spectrum/)」「效能特性」「進階參數」等不承諾等價。本地 Gemma 4 跟雲端 GPT-5 都能用同一套 API 呼叫、但回答品質天差地遠。

## 可觀察訊號與例子

最小可用請求：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:31b-coding-mtp-bf16",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

切換本地與雲端只改三個欄位：

| 欄位       | 雲端 OpenAI                 | 本地 Ollama                 |
| ---------- | --------------------------- | --------------------------- |
| API base   | `https://api.openai.com/v1` | `http://localhost:11434/v1` |
| API key    | `sk-xxxxxxx`                | 任意字串、本地多半略過驗證  |
| Model name | `gpt-5`                     | 本地 model tag              |

進階功能參差不齊：`response_format`、`tool_choice`、reasoning effort 等在本地伺服器的支援度視模型而定；雲端有的功能、本地未必能用。

## 判斷條件與後果

程式對 OpenAI 相容 API 寫一次時，換後端只改 API base、API key 與 model name 三個欄位，同一份程式就能接雲端、Ollama、LM Studio、llama.cpp 或 oMLX；OpenAI Python SDK、Vercel AI SDK 等多家 SDK 都支援設定 `base_url`。程式綁在某一家的專屬 API 上時，換後端要改寫呼叫的程式，IDE plugin 或 CLI 工具能接的後端也只剩那一家，所以這類工具以這份 API 為預設介面。相容只涵蓋 API 形狀：程式依賴 `response_format`、`tool_choice` 這類進階參數時，換到本地後端之後這些參數可能沒有作用，原因是它們在本地伺服器的支援度視模型而定。
