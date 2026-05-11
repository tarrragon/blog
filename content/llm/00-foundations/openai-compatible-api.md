---
title: "0.3 OpenAI 相容 API"
date: 2026-05-11
description: "為什麼幾乎所有本地 LLM 工具不用改就能切到本地：背後是同一套 API 形狀"
tags: ["llm", "foundations", "api"]
weight: 3
---

OpenAI 相容 API 是本地 LLM 生態能夠快速繁榮的關鍵基礎建設。OpenAI 在 2023 年定義的 `POST /v1/chat/completions` 介面成為事實標準後，後來幾乎所有本地推論伺服器（Ollama、LM Studio、llama.cpp、vLLM、oMLX）都實作同一份 API 規格；介面層工具只要支援這個規格，就能「不改一行程式」切換本地與雲端。

這個相容性決定了你的選擇空間。理解它的意義後，看到任何工具寫「支援 OpenAI 相容 API」時，你會知道這句話真正承諾的是什麼、不承諾的是什麼。

## 本章目標

讀完本章後，你應該能：

1. 看懂 `apiBase: http://localhost:11434/v1` 這類設定背後在做什麼。
2. 判斷一個介面層工具是否支援本地 LLM。
3. 知道「[OpenAI 相容](/llm/knowledge-cards/openai-compatible-api/)」承諾的範圍與邊界。
4. 用 curl 直接打本地 LLM 的 API 驗證它在跑。

## API 形狀的核心：chat completions

OpenAI 在 2023 年定義的 chat completions API 核心是這個請求格式：

```bash
curl http://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "寫一個 Python function 計算費氏數列"}
    ],
    "stream": true
  }'
```

回應是一連串 server-sent events，每個 event 包含一個 token chunk。

本地推論伺服器實作同樣的 endpoint 形狀，只是 host 換成 localhost、API key 不檢查或檢查 dummy 值：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:31b-coding-mtp-bf16",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "寫一個 Python function 計算費氏數列"}
    ],
    "stream": true
  }'
```

差別只有三點：

1. **host**：從 `api.openai.com` 換成 `localhost:11434`。
2. **model**：從 `gpt-5` 換成 `gemma4:31b-coding-mtp-bf16`。
3. **Authorization**：本地通常不檢查 API key，或接受任意值。

請求與回應的 JSON schema 完全一樣。這就是「OpenAI 相容」的字面意義。

## 為什麼這個相容性這麼重要

如果沒有 OpenAI 相容 API，每個介面層工具要支援新的伺服器就得寫專屬整合：Continue.dev 要為 Ollama 寫一份、為 LM Studio 寫一份、為 llama.cpp 寫一份、為雲端 OpenAI 寫一份、為 Anthropic 寫一份。每多一個工具就 N×M 的整合成本。

OpenAI 相容把這個成本拆成「介面層支援標準 API 一次 + 伺服器層實作標準 API 一次」，整合工作從 N×M 降到 N+M。後果是新伺服器（如 2024 年才出現的 oMLX）只要實作這份 API，馬上能被既有的所有介面層用上。

這也是為什麼幾乎所有 IDE plugin、CLI 工具、Web UI 都選擇 OpenAI 相容做 first-class citizen。Anthropic 自己的 API 形狀（messages、不同 streaming 格式）反而成為次要選項，介面層工具通常要為 Anthropic 寫額外的 adapter。

## 接本地 LLM 的最小設定

實際使用上，把任一個介面層工具切到本地 LLM 通常只要改三個欄位：

| 欄位       | 雲端 OpenAI 預設            | 切到本地 Ollama 後                       |
| ---------- | --------------------------- | ---------------------------------------- |
| API base   | `https://api.openai.com/v1` | `http://localhost:11434/v1`              |
| API key    | `sk-xxxxxxx`                | 任意字串，常用 `ollama` 或 `not-needed`  |
| Model name | `gpt-5`、`gpt-4o`           | Ollama 本地的 model tag，如 `gemma4:31b` |

接近真實的例子是 Continue.dev 的 `config.json`：

```json
{
  "models": [
    {
      "title": "Gemma 4 31B (local)",
      "provider": "ollama",
      "model": "gemma4:31b-coding-mtp-bf16",
      "apiBase": "http://localhost:11434"
    }
  ]
}
```

Continue.dev 內部會把 `provider: ollama` 翻成 OpenAI 相容請求送到 `apiBase`。如果你想用通用 OpenAI provider：

```json
{
  "models": [
    {
      "title": "Local LLM (via OpenAI-compatible)",
      "provider": "openai",
      "model": "gemma4:31b-coding-mtp-bf16",
      "apiBase": "http://localhost:11434/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

兩種寫法都會工作。`provider: ollama` 多一些 Ollama 特有功能（如 model auto-pull），`provider: openai` 比較通用、可以接任何 OpenAI 相容伺服器。

## 「OpenAI 相容」承諾什麼、不承諾什麼

相容承諾的是 **API 形狀** —— request schema、response schema、streaming 格式、錯誤碼大致一致。不承諾的是：

1. **模型能力**：本地 Gemma 4 31B 跟雲端 GPT-5 都能用同一套 API 呼叫，但回答品質天差地遠。
2. **效能特性**：本地的 TTFT、生字速度跟雲端完全不同，介面層感覺不到差別不代表速度一樣。
3. **進階參數**：OpenAI 自己的新功能（function calling 進階模式、structured output、reasoning effort 等）不一定被本地伺服器完整支援。常見問題是設定了 `tools` 參數但本地模型不會用。
4. **模型清單**：呼叫 `GET /v1/models` 回的清單、本地是你已下載的模型、雲端是 OpenAI 提供的模型；介面層要把兩邊清單視為各自獨立的資料。

接近真實的踩坑：

- 設定 `response_format: { type: "json_object" }` 強制 JSON 輸出，本地某些舊模型不認，會直接回普通文字。
- 設定 `tool_choice: "required"` 強制使用工具，本地許多模型不支援，行為退化成普通對話。
- 設定 `seed` 想拿確定性輸出，本地伺服器多半實作了，但雲端 OpenAI 並不保證每個 model 都尊重。

陷阱是把「相容」當成「等價」。寫程式碼時要假設本地伺服器可能不支援最新功能，做好降級處理。

## 用 curl 驗證本地 LLM 在跑

啟動 Ollama 並 pull 一個模型後，最快確認它在跑的方式是直接 curl：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:4b",
    "messages": [{"role": "user", "content": "Say hi in three languages."}],
    "stream": false
  }'
```

如果回的是 JSON 包含 `choices[0].message.content`，伺服器層正常。介面層連不上的時候，先用這個 curl 確認問題是介面層、伺服器層，還是模型本身。

需要驗證 streaming：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:4b",
    "messages": [{"role": "user", "content": "Count from 1 to 5."}],
    "stream": true
  }'
```

正常應該看到一連串 `data: {...}` 行，每行是一個 token chunk。

## 多伺服器並存：同時跑 Ollama 與 LM Studio

OpenAI 相容讓你可以同時在同一台 Mac 上跑多個伺服器，只要 port 不撞。常見配置：

| 伺服器    | 預設 port | 用途                         |
| --------- | --------- | ---------------------------- |
| Ollama    | 11434     | 日常寫 code 主力             |
| LM Studio | 1234      | 探索新模型、不影響主 server  |
| llama.cpp | 8080      | 進階測試、特殊量化           |
| oMLX      | 8000      | 長 context coding agent 場景 |

Continue.dev 的 `config.json` 可以同時列多個 model，每個 model 指向不同伺服器，UI 上下拉切換。這個能力讓「主力模型穩定跑、實驗模型隔離測試」變得直接。

## 不是 OpenAI 相容的本地工具

少數本地工具不走 OpenAI 相容，要特別注意：

1. **MLX 原生 Python API**：Apple 的 MLX framework 本身是 Python library，不是 HTTP server。需要自己 wrap 或用 `mlx_lm.server`（次要產品，功能不全）。
2. **早期 llama.cpp**：在 OpenAI 相容前就存在，原生 API 形狀不同；新版加上 `/v1/chat/completions` 後跟主流相容。
3. **某些研究專案**：直接 wrap PyTorch / Transformers，沒有 HTTP 層，要當 library 用。

遇到這類工具時，要評估「值不值得為它寫 adapter」。多數情況下選 OpenAI 相容的主流伺服器（Ollama、LM Studio）能省下大量整合成本。

## 小結

OpenAI 相容 API 是本地 LLM 三層架構能自由拼裝的基礎。它承諾 API 形狀一致、不承諾模型能力或效能等價；理解這個邊界後，後續所有「換伺服器」「換模型」「換介面」的操作都變得低成本。

下一章：[0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)，澄清三個常被混為一談的術語，避開網路上最常見的本地 LLM 認知陷阱。
