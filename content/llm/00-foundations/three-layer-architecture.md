---
title: "0.2 介面 / 伺服器 / 模型三層架構"
date: 2026-05-11
description: "把任何本地 LLM 工具放回正確的層級，用三層心智模型看懂工具關係"
tags: ["llm", "foundations", "architecture"]
weight: 2
---

本地 LLM 生態的核心心智模型是**三層架構**：介面層（CLI / UI / Plugin）→ 伺服器層（推論引擎與 API）→ 模型本身（權重檔）。三層之間有明確邊界，每層可以獨立替換；理解這個分層後，看到任何新工具都能立刻判斷它在解哪一層的問題。

對應到你已經熟悉的雲端世界：ChatGPT 網頁是介面層，OpenAI 的後端服務是伺服器層，GPT-5 模型是模型層。Cursor 是另一個介面層，連到的也是同一批雲端伺服器。介面跟伺服器各自獨立演化，這就是為什麼換介面不用換模型、換模型不用換介面。

本地 LLM 把這三層全部搬到你的 Mac 上，但分層關係不變。看懂這點，後面所有工具關係就清楚。

## 本章目標

讀完本章後，你應該能：

1. 看到任一個本地 LLM 工具，立刻判斷它屬於哪一層。
2. 理解為什麼可以「介面換、伺服器留」或「伺服器換、介面留」。
3. 看懂 `localhost:11434` 這類本地 API endpoint 的意義。
4. 對應雲端世界的工具，建立熟悉感橋接。

## 三層的責任邊界

| 層級     | 責任                                                 | 本地代表                                          | 雲端對應                             |
| -------- | ---------------------------------------------------- | ------------------------------------------------- | ------------------------------------ |
| 介面層   | 接收使用者輸入、顯示輸出、整合 IDE / 終端機          | Continue.dev、Open WebUI、aider、CLI              | ChatGPT 網頁、Cursor、Claude Desktop |
| 伺服器層 | 載入模型權重、處理 prompt、產生 token、提供 HTTP API | Ollama、LM Studio、llama.cpp `server`、oMLX、vLLM | OpenAI 後端服務、Anthropic 後端服務  |
| 模型層   | 神經網路權重檔本身                                   | Gemma 4、Qwen3、Llama 3.x、gpt-oss                | GPT-5、Claude Sonnet、Gemini         |

這張表是後續判讀新工具的基底。任何工具都可以放到這三層的某一格；少數工具同時跨多層（例如 LM Studio 內建介面跟伺服器），但它的功能仍可拆成三層去理解。

## 介面層：你實際在用的東西

介面層的責任是「人類能舒服地把任務送進去、把結果拿出來」。它本身不跑模型，只是把使用者輸入打包成 API 請求、把 API 回應顯示出來。

接近真實的例子：

- **Continue.dev**：VS Code 擴充套件，把 Cmd+L 開啟側邊對話框、Cmd+I 觸發 inline 編輯。背後送的是 OpenAI 相容 API 請求，target 可以是本地 Ollama 也可以是雲端 OpenAI。
- **aider**：CLI 工具，把 git 倉庫狀態跟 prompt 一起打包送進 LLM，再把回應的 diff apply 到本機檔案。背後也是送 API 請求。
- **Open WebUI**：類 ChatGPT 風格的網頁介面，跑在本機 Docker 裡，連到本地或遠端的 LLM API。
- **CLI 直接呼叫**：`ollama run gemma4:31b` 在終端機開一個對話 session，本身也是一個介面層。

介面層的選擇影響日常使用體驗，但完全不影響推論速度或品質。換介面不用換模型，這就是分層的好處。

## 伺服器層：本地 LLM 的核心

伺服器層是本地 LLM 生態的核心。它的責任是：把模型權重從磁碟載入記憶體、接收 HTTP API 請求、處理 prompt、跑推論、把生成的 token 流回客戶端。

接近真實的例子：

- **Ollama**：最主流的本地推論伺服器，預設聽 `localhost:11434`，提供 OpenAI 相容 API 與自己的原生 API。內建 model registry，`ollama pull gemma4:31b` 會自動下載權重檔。
- **LM Studio**：GUI 工具，內建模型瀏覽器與本地伺服器。可以在 UI 上開啟 server，預設聽 `localhost:1234`。適合喜歡可視化操作、不熟悉終端機的使用者。
- **llama.cpp `server`**：底層推論引擎附帶的 HTTP server，需要手動編譯與配置。Ollama 內部其實是用 llama.cpp 當推論引擎。
- **oMLX**：建在 MLX 之上的特化伺服器，主打 paged SSD KV cache，針對 coding agent 長 context 場景的首字延遲優化。詳見 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)。

伺服器層的選擇影響：

1. **速度**：不同伺服器對量化、KV cache、speculative decoding 的支援度不同。
2. **能跑哪些模型**：每個伺服器支援的模型格式不同（GGUF、MLX、Safetensors 等）。
3. **API 形狀**：多數本地伺服器同時提供「OpenAI 相容」跟「自家原生」兩套 API。詳見 [0.3 OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)。

陷阱是把伺服器跟模型混為一談。「Ollama 跑得快不快」這句話沒意義，要問「Ollama 跑某個模型在某台 Mac 上跑多快」。伺服器是執行引擎，模型是被執行的對象。

## 模型層：權重檔本身

模型層就是神經網路的權重檔。本身只是一堆數字，沒有伺服器就無法執行；但同一個模型可以被不同伺服器載入，前提是格式相容。

接近真實的例子：

- **Gemma 4 31B**：Google 釋出的開源模型，32 billion 參數。權重檔可以是 `gemma-3-31b-it-Q4_K_M.gguf`（GGUF 格式、Q4 量化）或 `mlx-community/gemma-3-31b-it-4bit`（MLX 格式）。
- **Qwen3-Coder 30B**：Alibaba 釋出的 coding 專用模型，SWE-bench 表現接近 GPT-4。
- **Llama 3.x 系列**：Meta 釋出的開源模型，是早期本地 LLM 生態的主力。
- **gpt-oss 20B**：OpenAI 釋出的開源版本，2025 年發布。

模型層的關鍵屬性：

1. **參數規模**（B = billion）：7B、14B、31B、70B 等。規模越大能力越強，但記憶體佔用、推論速度成本也越高。
2. **量化等級**：bf16、Q8、Q5_K、Q4_K 等。同模型不同量化，記憶體與品質的取捨不同。
3. **格式**：GGUF（llama.cpp 與 Ollama 主流）、MLX（Apple 框架）、Safetensors（Hugging Face 通用）等。不同伺服器支援的格式不同。
4. **訓練目的**：[base model](/llm/knowledge-cards/base-model/)、[instruction-tuned](/llm/knowledge-cards/instruction-tuned/)、coding-tuned 等。寫 code 適合 instruction-tuned + coding 版本；base model 適合下游微調研究、跟著 prompt 走的能力較弱。

模型選擇影響能力與速度。同樣 32GB Mac 跑 Gemma 4 31B 跟 Qwen3-Coder 30B，兩個模型擅長的任務不同，速度也不同。詳見 [模型選型章節](/llm/01-local-llm-services/model-selection-priority/)。

## 三層如何拼裝：常見組合

理解三層後，本地 LLM 的所有「組合」都變得簡單。下表是幾個常見組合：

| 介面層       | 伺服器層  | 模型層           | 用途                         |
| ------------ | --------- | ---------------- | ---------------------------- |
| Continue.dev | Ollama    | Gemma 4 31B MTP  | VS Code 寫 code 主力         |
| Continue.dev | LM Studio | Qwen3-Coder 30B  | LM Studio 派的 VS Code 整合  |
| aider        | Ollama    | Qwen3-Coder 30B  | CLI 寫 code、git-aware       |
| Open WebUI   | Ollama    | Gemma 4 31B      | 類 ChatGPT 網頁、團隊共用    |
| Ollama CLI   | Ollama    | Llama 3.3 70B Q3 | 終端機直接對話、極限模型壓榨 |
| LM Studio UI | LM Studio | 任意             | 純探索新模型、GUI 派         |

注意三件事：

1. 介面跟伺服器之間用 HTTP API 通訊，所以介面層可以同時連多個伺服器，或一個伺服器服務多個介面層。
2. 同一個介面（如 Continue.dev）可以同時設定本地 Ollama 跟雲端 OpenAI，根據任務切換。
3. LM Studio 自己同時是介面 + 伺服器，所以表上有兩列；但它的伺服器部分也可以對外 expose，讓其他介面（如 Continue.dev）連進來。

## 雲端對應關係：建立熟悉感橋接

下表把本地三層對應到雲端世界，幫助建立直覺：

| 本地                                     | 雲端對應                                       |
| ---------------------------------------- | ---------------------------------------------- |
| Continue.dev                             | Cursor                                         |
| Open WebUI                               | ChatGPT 網頁                                   |
| Ollama / LM Studio (server 部分)         | OpenAI / Anthropic 後端服務                    |
| Ollama API on localhost:11434            | api.openai.com                                 |
| Gemma 4 31B                              | GPT-5、Claude Sonnet 4.6                       |
| `gemma4:31b-coding-mtp-bf16`（模型 tag） | `gpt-5`、`claude-sonnet-4-6`（API model name） |

這個對應的關鍵啟示是：**Cursor 跟 Continue.dev 都是介面層**，差別在於 Cursor 預設綁雲端、Continue.dev 預設綁本地，但兩者的責任邊界一樣。換句話說，要在 VS Code 裡接本地 LLM，不需要找「本地版的 Cursor」這種神奇東西，找一個能設定 OpenAI 相容 endpoint 的介面層就好。

## 小結

本地 LLM 的三層架構（介面 / [推論伺服器](/llm/knowledge-cards/inference-server/) / 模型）跟雲端世界完全對應、只是全部跑在你的 Mac 上。理解三層後、後續看到任何工具都能立刻判斷它屬於哪一層；換工具時也知道該換哪一層、其他層可以保留。

下一章：[0.3 OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)，解釋為什麼三層之間能自由組合，背後是同一套 API 形狀。
