---
title: "本地 LLM 寫 code 實務指南"
date: 2026-05-11
description: "從心智模型、術語澄清、硬體現實到 Mac 本地 LLM 服務的安裝、整合 VS Code 與模型選型"
tags: ["llm", "local-llm", "mac", "apple-silicon", "ollama"]
weight: 36
---

本指南的核心目標是把「在 Apple Silicon Mac 上跑本地 LLM 寫 code」這件事拆成可決策、可實作、可期望管理的工程問題。網路上的本地 LLM 文章常把推論框架、加速技巧與伺服器混為一談；本指南先把這些名詞放回正確的層級，再回答硬體記憶體、模型選擇、VS Code 整合與雲端 / 本地分工問題。

本指南預設讀者已經會用過雲端 LLM（ChatGPT、Claude），手上有一台 Apple Silicon Mac（M1 ~ M4），熟悉終端機操作，主要目的是把本地 LLM 接到 VS Code 輔助寫 code。文章不販賣本地 LLM 焦慮，也不誇大它能取代雲端的程度；它的責任是給一條最短可行路徑，並標出每個階段的取捨。

## 教材邊界

| 類型           | 放在本指南                                                                                                                                                                | 不放在本指南                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 心智模型       | 本地 vs 雲端的差異、為何 LLM 生字慢、三層架構（介面 / 伺服器 / 模型）、[OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)                                      | 模型架構數學細節、Transformer 內部運算公式              |
| 術語澄清       | [MLX](/llm/00-foundations/mlx-mtp-omlx/)、[MTP](/llm/00-foundations/mlx-mtp-omlx/)、[oMLX](/llm/00-foundations/mlx-mtp-omlx/)、speculative decoding、量化、KV cache、TTFT | 訓練流程、RLHF、post-training fine-tuning               |
| 硬體現實       | [記憶體預算與模型大小](/llm/00-foundations/hardware-memory-budget/)、量化選擇、首字延遲、風扇與功耗                                                                       | NVIDIA / AMD GPU、Linux server inference、雲端 GPU 租用 |
| 本地推論伺服器 | [Ollama](/llm/01-local-llm-services/ollama/)、[LM Studio](/llm/01-local-llm-services/lm-studio/)、[llama.cpp](/llm/01-local-llm-services/llama-cpp/)                      | vLLM、TGI、Triton 等資料中心級 inference server         |
| 編輯器整合     | [Continue.dev + VS Code](/llm/01-local-llm-services/vscode-continue-integration/)、Cursor 對應關係                                                                        | JetBrains 全套整合、Vim / Emacs 進階 plugin             |
| 模型挑選       | [coding 場景的模型優先順序](/llm/01-local-llm-services/model-selection-priority/)、量化等級對體感影響                                                                     | benchmark 跑分方法論、模型訓練資料比較                  |
| 期望管理       | [本地 LLM 的擅長領域與分工](/llm/01-local-llm-services/expectation-management/)、混用雲端的時機                                                                           | LLM 通用能力評估、AGI 預測                              |

## 學習路線

本指南分成兩大模組加一組前置卡片。先讀基礎知識建立心智模型、再進入本地模型服務的安裝與應用；任一節可以單獨閱讀。讀章節時遇到陌生詞彙、可以隨時跳到 [前置知識卡片](/llm/knowledge-cards/) 補完、再回到章節繼續。

### [前置知識卡片](/llm/knowledge-cards/)

用原子化卡片整理 [token](/llm/knowledge-cards/token/)、[自回歸](/llm/knowledge-cards/autoregressive/)、[KV cache](/llm/knowledge-cards/kv-cache/)、[量化](/llm/knowledge-cards/quantization/)、[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[MTP](/llm/knowledge-cards/mtp/)、[MLX](/llm/knowledge-cards/mlx/)、[推論伺服器](/llm/knowledge-cards/inference-server/)、[OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)、[memory bandwidth](/llm/knowledge-cards/memory-bandwidth/)、[統一記憶體](/llm/knowledge-cards/unified-memory/)、[TTFT](/llm/knowledge-cards/ttft/)、[prefill](/llm/knowledge-cards/prefill/)、[context window](/llm/knowledge-cards/context-window/)、[Transformer](/llm/knowledge-cards/transformer/)、[Diffusion](/llm/knowledge-cards/diffusion/) 等核心概念。章節文章專注情境推導、術語背景交由卡片維持一致。

### [模組零：基礎知識與心智模型](/llm/00-foundations/)

整理本地 vs 雲端 LLM 的差異、自回歸架構與記憶體頻寬瓶頸、介面 / 伺服器 / 模型三層心智模型、OpenAI 相容 API 為何重要、MLX / MTP / oMLX 三個容易搞混的術語、Apple Silicon Mac 記憶體與模型大小的對應關係、判讀本地 LLM 資訊的五個框架。

### [模組一：本地 LLM 服務的安裝與應用](/llm/01-local-llm-services/)

整理 Ollama、LM Studio、llama.cpp 三個主流推論伺服器的現況差異與安裝路徑、用 Continue.dev 把本地 LLM 接到 VS Code 的完整步驟、寫 code 場景下模型選型的優先順序、本地模型的期望管理、想進一步玩 coding agent、Web UI、產圖時的延伸方向。

## 兩個模組怎麼配合

模組零的責任是建立判讀語言。讀完之後你會知道：看到「llama.cpp 整合 Gemma 4 MTP」這種句子時要先確認是 server 還是模型；看到「MLX 加速」時要分辨講的是 framework 還是某個 server；看到「24GB 能跑 70B」這種說法時要追問是哪種量化、留多少給系統。

模組一的責任是把語言落地到可操作步驟。每個 server 都會回答：怎麼裝、怎麼選模型、API 長什麼樣、有什麼坑、適合誰、不適合誰。最後用模型選型章節與期望管理章節，幫你決定「現在裝哪個、用哪個模型、什麼時候該切回雲端」。

## 適合的讀者

| 背景                                      | 適合程度 | 建議起點                                                                                                                         |
| ----------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 用過 ChatGPT / Claude、沒碰過本地模型     | 直接適合 | [模組零](/llm/00-foundations/) 從頭讀                                                                                            |
| 裝過 Ollama 但被網路上的術語混淆          | 直接適合 | [MLX / MTP / oMLX 區分](/llm/00-foundations/mlx-mtp-omlx/) + [常見誤解](/llm/00-foundations/common-misconceptions/)              |
| 想知道 24GB / 32GB Mac 該選哪個模型       | 直接適合 | [硬體記憶體預算](/llm/00-foundations/hardware-memory-budget/) + [模型選型](/llm/01-local-llm-services/model-selection-priority/) |
| 想用本地 LLM 完全取代 Claude / GPT-5      | 部分適合 | [期望管理](/llm/01-local-llm-services/expectation-management/) 先看完再決定                                                      |
| 想在 Linux server / NVIDIA GPU 跑推論     | 不適合   | 本指南只討論 Apple Silicon Mac，請另尋資料中心 inference 教材                                                                    |
| 想跑 Stable Diffusion / Midjourney 等產圖 | 不適合   | 產圖是 Diffusion 架構、跟寫 code 用的 Transformer 不同，請另尋 ComfyUI / Draw Things 教材                                        |

## 用語約定

本指南使用的關鍵術語在第一次出現時都附原文。為避免歧義，下列詞彙在本指南內固定指涉：

1. **本地 LLM**：跑在使用者自己 Mac 上的大型語言模型推論，不上傳請求到第三方雲端。
2. **推論伺服器**（inference server）：負責載入模型權重、處理 prompt、產生 token 的常駐程式，例如 Ollama、LM Studio 內建 server、llama.cpp `server`。
3. **介面層**：使用者實際打字互動的工具，例如 VS Code + Continue.dev、CLI、Web UI。介面層透過 API 跟推論伺服器溝通。
4. **模型**（model）：權重檔本身，例如 `gemma4:31b`、`qwen3-coder:30b`。模型可以在不同推論伺服器之間共用，前提是格式相容。
5. **量化**（quantization）：把模型權重從高精度（如 bf16）壓成低精度（如 Q4）以減少記憶體佔用，代價是少許品質下降。

## 不在本指南內的主題

本指南不討論訓練、fine-tuning、RLHF、向量資料庫、RAG 系統設計、多模態（圖片 / 語音）模型、雲端 GPU 租用、Kubernetes 上的 inference 部署。這些主題各自獨立、邊界不同，硬塞進來只會讓 Mac 本地寫 code 這條最短路徑被淹沒。

若讀完本指南後想往這些方向走，可從以下入口開始：

1. 想用本地 LLM 做檢索：先把 Ollama + Continue.dev 跑穩，再讀 LlamaIndex / LangChain 的 RAG 教學。
2. 想跑 coding agent：先讀 [延伸方向](/llm/01-local-llm-services/extension-paths/)，了解 aider、Cline 等工具的定位差異。
3. 想跑產圖模型：Diffusion 跟 Transformer 是不同架構，請另尋 ComfyUI / Draw Things / Diffusers 教材，不是換 model 就好。

---

_文件版本：v0.1.0_
_最後更新：2026-05-11_
_系列狀態：兩個模組初稿建立中_
