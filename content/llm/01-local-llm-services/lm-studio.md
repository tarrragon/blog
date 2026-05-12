---
title: "1.1 LM Studio：GUI 探索模型"
date: 2026-05-11
description: "GUI 取向的本地推論伺服器：內建模型瀏覽器、speculative decoding 設定面板、適合探索新模型"
tags: ["llm", "lm-studio", "server"]
weight: 1
---

LM Studio 跟 Ollama 一樣屬於[本地推論伺服器層](/llm/00-foundations/three-layer-architecture/)、但定位完全不同：Ollama 是 CLI-first、LM Studio 是 GUI-first。它的核心承諾是「不打開終端機也能玩本地 LLM」、特別適合對 Hugging Face model hub（社群最大的開源模型 registry、提供權重檔下載與比較）、[量化](/llm/knowledge-cards/quantization/)等級、[speculative decoding](/llm/knowledge-cards/speculative-decoding/) 還在摸索階段的使用者。

對寫 code 場景來說，LM Studio 不一定是日常主力（Ollama 通常更穩、生態更成熟），但它在「探索新模型」「視覺化看推論參數」「拿來教其他人本地 LLM」這幾個情境上明顯佔優勢。本章說明它的安裝、模型瀏覽器、server 模式啟用，以及跟 Ollama 並存的配置。

## 本章目標

讀完本章後，你應該能：

1. 安裝 LM Studio 並下載第一個模型。
2. 在 GUI 跟模型對話、調整參數。
3. 啟用 LM Studio 的 OpenAI 相容 server 模式。
4. 判斷你的工作流適不適合用 LM Studio 當主力。
5. 讓 LM Studio 與 Ollama 並存。

## 安裝

LM Studio 是商業軟體（個人使用免費），不在 Homebrew core repo 裡。直接從官網下載：

1. 開 [lmstudio.ai](https://lmstudio.ai)
2. 下載 macOS（Apple Silicon）版本
3. 把 LM Studio.app 拖到 Applications
4. 第一次開啟會被 macOS 安全提示擋，到「系統設定 > 隱私權與安全性」放行

裝完開啟 app，會看到三個主要分頁：

- **Discover**：搜尋 Hugging Face model hub、下載模型
- **My Models**：管理已下載模型
- **Chat / Developer**：跟模型對話、啟用 server

## 下載第一個模型

Discover 分頁把 Hugging Face 模型搜尋、[量化等級](/llm/knowledge-cards/quantization/)挑選、記憶體適配判讀集中在同一個面板。在 Discover 分頁搜尋模型名（例如 `gemma-4`）、會列出 Hugging Face 上的對應 repo：

| 顯示資訊  | 解讀                                                       |
| --------- | ---------------------------------------------------------- |
| Repo 名稱 | 例如 `bartowski/gemma-4-31b-it-GGUF`                       |
| 量化等級  | Q4_K_M、Q5_K_M、Q8 等，列在每個檔案旁邊                    |
| 檔案大小  | 直接顯示 GB 數，方便判斷是否塞得進記憶體                   |
| 適配建議  | LM Studio 會根據你 Mac 記憶體標「Recommended / Too Large」 |

選一個合適量化等級點下載。Q4_K_M 在多數場景是甜蜜點；32GB Mac 跑 31B Q5_K_M 也順暢。下載中可以繼續操作其他功能。

陷阱：

1. **Repo 來源要看**。Hugging Face 上同一個模型有多個社群重新封裝的 repo。`google/gemma-4-...` 是官方 repo；`bartowski/...` 等是社群常見的高品質 quant 提供者。挑下載量高、最近更新的 repo 較安全。
2. **不是所有檔案都要下載**。一個 repo 可能有 5 ~ 10 個量化檔案，下載你選的那個就好。LM Studio UI 有時讓人誤以為要全選。
3. **下載完成後檢查路徑**：預設下載到 `~/.cache/lm-studio/models/`、跟 Ollama 的 `~/.ollama/models/` 分開。兩邊 model storage 各自獨立、想在兩個伺服器都用同一個模型要分別下載。

## Chat 分頁與推論參數調整

下載完到 Chat 分頁、左上角 model selector 選剛下載的模型。LM Studio 會把模型載入記憶體（30 ~ 60 秒）、然後就能對話。

右側面板提供推論參數調整：

| 參數               | 預設             | 何時調整                                         |
| ------------------ | ---------------- | ------------------------------------------------ |
| Temperature        | 0.7              | 寫 code 建議 0.2 ~ 0.4 增加確定性                |
| Top-K              | 40               | 通常不動                                         |
| Top-P              | 0.95             | 通常不動                                         |
| Repeat Penalty     | 1.1              | 模型一直重複時微調                               |
| Context Length     | 模型支援的最大值 | 短 context 任務可以調小省記憶體                  |
| GPU Offload Layers | Auto             | M-series Mac 留 Auto，Apple Silicon 是統一記憶體 |

對寫 code 場景的關鍵調整是 **Temperature 降到 0.2 ~ 0.4**，可以讓回答更穩定、減少幻覺。預設 0.7 是給創意寫作的設定。

## Speculative decoding 設定面板

LM Studio 內建 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 的 UI 設定。在 model 載入頁面下方有 **Draft Model** 設定區：

1. 選 target model（主力，例如 Gemma 4 31B）
2. 選 draft model（小模型，例如 Gemma 4 E4B）
3. 啟用 speculative decoding

[Speculative decoding](/llm/knowledge-cards/speculative-decoding/) 真的加速需要 target 與 [drafter](/llm/knowledge-cards/drafter-model/) 用同一個 tokenizer。Gemma 4 31B 配 Gemma 4 E4B 可以工作；Gemma 4 配 Llama 因 tokenizer 不同無法配對。LM Studio UI 會自動過濾相容的 draft 候選。

跟 Ollama 比，LM Studio 的優勢是「能看到並調整每個推論細節」。劣勢是「Gemma 4 的官方 MTP drafter 整合不是一鍵」，要自己挑 draft model。多數使用者用 Ollama 的 `gemma4:31b-coding-mtp-bf16` 一行解決就好；想自己組合 target + drafter 的進階使用者選 LM Studio。

## 啟用 Server 模式

Server 模式是 LM Studio 暴露 OpenAI 相容 API 的開關、預設關閉以避免 GUI 使用者誤開網路 port。讓 VS Code 等介面層接 LM Studio、要開 **Local Server** 模式：

1. 切到 Developer 分頁（左側 icon 像 `</>`）
2. 在頂部 model selector 選要 serve 的模型
3. 點 **Start Server**

預設聽 `localhost:1234`，提供 OpenAI 相容 API。

驗證：

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31b-it",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

回應的 JSON 應該包含 `choices[0].message.content`。

陷阱：

1. **Server 跟 GUI 同生命週期**。關閉 LM Studio 視窗或登出 macOS 會停止 server、IDE 連不上。修法：日常常駐改用 [Ollama 的 launchd service 模式](/llm/01-local-llm-services/ollama/#背景常駐launchd-service)、LM Studio 只在桌面 session 啟動探索。
2. **CORS 預設關**。要從瀏覽器（如 Open WebUI 跑在不同 port）連，要去 Server 設定打開 CORS。
3. **Model name 不是 tag**。LM Studio 在 API 用的 model name 是檔名（如 `gemma-4-31b-it`），跟 Ollama 的 tag 格式不同。

## 與 Ollama 並存

LM Studio（port 1234）跟 Ollama（port 11434）port 不同，可以同時跑。在 Continue.dev 的 `config.json` 可以同時列：

```json
{
  "models": [
    {
      "title": "Ollama: Gemma 4 31B MTP",
      "provider": "ollama",
      "model": "gemma4:31b-coding-mtp-bf16",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "LM Studio: Qwen3-Coder 30B",
      "provider": "openai",
      "model": "qwen3-coder-30b",
      "apiBase": "http://localhost:1234/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

UI 上可以下拉切換 model。這個設計讓你「Ollama 跑主力、LM Studio 跑實驗模型」，兩條工作流不互相干擾。

## LM Studio 適合誰

| 你是這樣的人                          | LM Studio 適合度                     |
| ------------------------------------- | ------------------------------------ |
| GUI 派、不愛打 CLI                    | 高                                   |
| 想看推論參數細節並調整                | 高                                   |
| 想頻繁探索 Hugging Face 上新模型      | 高                                   |
| 想自己組合 target + drafter           | 高                                   |
| 想 server 隨開機常駐                  | 低（GUI app 不適合 daemon）          |
| 想跟 Anthropic Claude Code 等工具整合 | 中（API 相容但 model name 規則不同） |
| 已經習慣 Ollama CLI                   | 低（除非有探索需求）                 |

簡單的建議：**LM Studio 適合當「副廚」、Ollama 適合當「主廚」**。日常工作流用 Ollama 跑主力模型、需要探索新東西時開 LM Studio。

## 何時改回 Ollama 或 llama.cpp

LM Studio 的 GUI 定位在以下情境會變成阻礙、建議改用其他伺服器：

| 情境                                    | 建議路由                                                                                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Headless 環境（無 GUI 桌機 / 遠端 SSH） | [Ollama](/llm/01-local-llm-services/ollama/) — CLI-first、能用 launchd / systemd 跑                 |
| CI / 自動化跑 batch 推論                | Ollama 或 llama-server — 可用 systemd / Docker 起、不依賴 GUI session                               |
| 需要 daemon 24/7 常駐                   | Ollama 配 [launchd service](/llm/knowledge-cards/launchd-service/) — LM Studio 視窗關閉 server 就停 |
| 自己量化模型 / 跑特殊冷門模型           | [llama.cpp](/llm/01-local-llm-services/llama-cpp/) — 直接面對 GGUF / quantize 工具                  |
| 想用 Ollama Library 的 1-tag 即裝       | Ollama — `ollama run gemma4:31b-coding-mtp-bf16` 已內含 MTP drafter、LM Studio 需手動挑 draft model |

LM Studio 的最佳定位是「需要 GUI、桌面 session 內探索、有人在電腦前操作」的場景；任何「沒人看著 / 後台跑 / 跨機器 daemon」的需求、Ollama 通常更穩。

## 跟 Anthropic Claude API 的對比

如果你習慣 Claude 的工具用法（Anthropic Console、Claude Code）、LM Studio 的 GUI 體驗比較像 Anthropic Console：可以調 system prompt、看 token 計數、儲存對話。兩者都用 [OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/) 形狀（Anthropic 自有 messages API 是另一條路徑、LM Studio 不接 Anthropic 格式）。差別是：

| 維度         | Anthropic Console                  | LM Studio                     |
| ------------ | ---------------------------------- | ----------------------------- |
| 模型         | Claude Sonnet、Opus、Haiku（雲端） | 自己下載的本地模型            |
| 隱私         | 走 Anthropic 雲端                  | 完全本地                      |
| 計費         | 按 token 計費                      | 一次性硬體                    |
| 進階功能     | Tools、Vision、Computer Use 完整   | 視模型而定，多半較陽春        |
| Streaming UI | 流暢                               | 流暢                          |
| Prompt 偵錯  | Workbench 完整                     | Chat / Developer 分頁可調參數 |

LM Studio 對寫 code 場景不是 Anthropic Console 的替代品，但作為「本地版 console」的體驗很完整。

## 小結：LM Studio 的副廚定位

LM Studio 是 GUI-first 的本地推論伺服器、定位跟 Ollama 互補。對探索新模型、調整推論參數、自組 speculative decoding 設定的使用者來說、它比 Ollama 更直覺；對日常寫 code 主力來說、Ollama 通常更穩。建議讓兩個並存、各司其職。

下一章：[1.2 llama.cpp 底層引擎](/llm/01-local-llm-services/llama-cpp/)，澄清網路上「llama.cpp 才是真本地」這類迷思。
