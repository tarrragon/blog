---
title: "本地 LLM 寫 code 實務指南"
date: 2026-05-11
description: "從心智模型、術語澄清、硬體現實到 Mac 本地 LLM 服務的安裝、整合 VS Code、模型選型、數學與理論基礎"
tags: ["llm", "local-llm", "mac", "apple-silicon", "ollama", "foundations", "transformer", "inference"]
weight: 36
---

本指南的核心目標是把「在 Apple Silicon Mac 上跑本地 LLM 寫 code」這件事拆成可決策、可實作、可期望管理的工程問題。網路上的本地 LLM 文章常把推論框架、加速技巧與伺服器混為一談；本指南先把這些名詞放回正確的層級，再回答硬體記憶體、模型選擇、VS Code 整合與雲端 / 本地分工問題。

本指南預設讀者已經會用過雲端 LLM（ChatGPT、Claude），手上有一台 Apple Silicon Mac（M1 ~ M4），熟悉終端機操作，主要目的是把本地 LLM 接到 VS Code 輔助寫 code。文章不販賣本地 LLM 焦慮，也不誇大它能取代雲端的程度；它的責任是給一條最短可行路徑，並標出每個階段的取捨。

模組零跟模組一覆蓋「裝跟用」這條最短路徑。想懂底層的讀者、模組二（[數學基礎](/llm/02-math-foundations/)）跟模組三（[LLM 理論基礎](/llm/03-theoretical-foundations/)）提供完整理論圖像、並推薦 MIT / Stanford / Karpathy 等公開課作為深入入口。模組四（[應用層原理](/llm/04-applications/)）整理 LLM 作為系統元件的設計取捨：RAG、tool use、agent、應用層協議與 workflow 編排模式、刻意只寫跨工具世代不變的概念。

## 教材邊界

| 類型           | 放在本指南                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 不放在本指南                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 心智模型       | 本地 vs 雲端的差異、為何 LLM 生字慢、三層架構（介面 / 伺服器 / 模型）、[OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)                                                                                                                                                                                                                                                                                                                                                                                                                                      | NVIDIA / AMD GPU 部署                                             |
| 術語澄清       | [MLX](/llm/00-foundations/mlx-mtp-omlx/)、[MTP](/llm/00-foundations/mlx-mtp-omlx/)、[oMLX](/llm/00-foundations/mlx-mtp-omlx/)、[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[量化](/llm/knowledge-cards/quantization/)、[KV cache](/llm/knowledge-cards/kv-cache/)、[TTFT](/llm/knowledge-cards/ttft/)                                                                                                                                                                                                                                             | post-training fine-tuning 細節                                    |
| 硬體現實       | [記憶體預算與模型大小](/llm/00-foundations/hardware-memory-budget/)、量化選擇、首字延遲、風扇與功耗                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Linux server inference、雲端 GPU 租用                             |
| 本地推論伺服器 | [Ollama](/llm/01-local-llm-services/ollama/)、[LM Studio](/llm/01-local-llm-services/lm-studio/)、[llama.cpp](/llm/01-local-llm-services/llama-cpp/)                                                                                                                                                                                                                                                                                                                                                                                                                      | vLLM、TGI、Triton 等資料中心級 inference server                   |
| 編輯器整合     | [Continue.dev + VS Code](/llm/01-local-llm-services/vscode-continue-integration/)、Cursor 對應關係                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | JetBrains 全套整合、Vim / Emacs 進階 plugin                       |
| 模型挑選       | [coding 場景的模型優先順序](/llm/01-local-llm-services/model-selection-priority/)、量化等級對體感影響                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | benchmark 跑分方法論的完整推導                                    |
| 期望管理       | [本地 LLM 的擅長領域與分工](/llm/01-local-llm-services/expectation-management/)、混用雲端的時機                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | LLM 通用能力評估、AGI 預測                                        |
| 數學基礎       | [線性代數](/llm/02-math-foundations/linear-algebra-for-llm/)、[機率與資訊論](/llm/02-math-foundations/probability-and-information/)、[最佳化](/llm/02-math-foundations/calculus-and-optimization/)、[數值精度](/llm/02-math-foundations/numerical-precision/) 在 LLM 中的角色                                                                                                                                                                                                                                                                                             | 完整數學證明、測度論等屬於數學系範圍的主題                        |
| 理論基礎       | [神經網路](/llm/03-theoretical-foundations/neural-network-basics/)、[embedding](/llm/03-theoretical-foundations/embedding-spaces/)、[attention](/llm/03-theoretical-foundations/attention-mechanism/)、[Transformer](/llm/03-theoretical-foundations/transformer-architecture/)、[訓練流程](/llm/03-theoretical-foundations/training-pipeline/)、[sampling](/llm/03-theoretical-foundations/sampling-and-decoding/)、[tokenization](/llm/03-theoretical-foundations/tokenization-algorithms/)、[跨語言原理](/llm/03-theoretical-foundations/cross-language-tokenization/) | 多模態擴展、最新研究細節交給 Stanford CS25                        |
| 應用層原理     | [RAG](/llm/04-applications/rag-principles/)、[Tool use](/llm/04-applications/tool-use-principles/)、[Agent 架構](/llm/04-applications/agent-architecture/)、[應用層協議](/llm/04-applications/application-protocols/)、[Workflow 編排](/llm/04-applications/workflow-patterns/)                                                                                                                                                                                                                                                                                           | 具體 framework 教學（LangChain / LlamaIndex）、prompt engineering |
| 隱私 / 排錯    | [隱私資料流](/llm/00-foundations/privacy-data-flow/)、[排錯方法論](/llm/01-local-llm-services/troubleshooting/)                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 具體合規法規逐條檢核                                              |
| 進一步學習     | [數學公開課推薦](/llm/02-math-foundations/going-deeper-math/)、[LLM 理論公開課推薦](/llm/03-theoretical-foundations/going-deeper-theory/)                                                                                                                                                                                                                                                                                                                                                                                                                                 | （交給推薦的課程跟書籍）                                          |

## 學習路線

本指南分成四個模組加一組前置卡片。讀者依目的選讀：

- 想快速「裝跟用」：讀模組零 + 模組一就夠。
- 想懂底層：再進入模組二跟模組三。
- 想跟最新進展接軌：讀完所有模組、再進入推薦的公開課程跟必讀 paper。

### [前置知識卡片](/llm/knowledge-cards/)

用原子化卡片整理 [token](/llm/knowledge-cards/token/)、[自回歸](/llm/knowledge-cards/autoregressive/)、[KV cache](/llm/knowledge-cards/kv-cache/)、[量化](/llm/knowledge-cards/quantization/)、[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[MTP](/llm/knowledge-cards/mtp/)、[MLX](/llm/knowledge-cards/mlx/)、[推論伺服器](/llm/knowledge-cards/inference-server/)、[OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)、[memory bandwidth](/llm/knowledge-cards/memory-bandwidth/)、[統一記憶體](/llm/knowledge-cards/unified-memory/)、[TTFT](/llm/knowledge-cards/ttft/)、[prefill](/llm/knowledge-cards/prefill/)、[context window](/llm/knowledge-cards/context-window/)、[Transformer](/llm/knowledge-cards/transformer/)、[Diffusion](/llm/knowledge-cards/diffusion/) 等核心概念。章節文章專注情境推導、術語背景交由卡片維持一致。

### [模組零：基礎知識與心智模型](/llm/00-foundations/)

整理本地 vs 雲端 LLM 的差異、自回歸架構與記憶體頻寬瓶頸、介面 / 伺服器 / 模型三層心智模型、OpenAI 相容 API 為何重要、MLX / MTP / oMLX 三個容易搞混的術語、Apple Silicon Mac 記憶體與模型大小的對應關係、判讀本地 LLM 資訊的五個框架。

### [模組一：本地 LLM 服務的安裝與應用](/llm/01-local-llm-services/)

整理 Ollama、LM Studio、llama.cpp 三個主流推論伺服器的現況差異與安裝路徑、用 Continue.dev 把本地 LLM 接到 VS Code 的完整步驟、寫 code 場景下模型選型的優先順序、本地模型的期望管理、想進一步玩 coding agent、Web UI、產圖時的延伸方向。

### [模組二：LLM 的數學基礎](/llm/02-math-foundations/)

整理 LLM 推論背後的數學工具：[線性代數](/llm/02-math-foundations/linear-algebra-for-llm/)（向量、矩陣、空間）、[機率與資訊論](/llm/02-math-foundations/probability-and-information/)（softmax、cross-entropy、KL、perplexity）、[微積分與最佳化](/llm/02-math-foundations/calculus-and-optimization/)（gradient、SGD / Adam）、[數值精度](/llm/02-math-foundations/numerical-precision/)（fp32 / bf16 / Q4 / Q8 的取捨）。每章末尾接到[公開課推薦](/llm/02-math-foundations/going-deeper-math/)。

### [模組三：LLM 的理論基礎](/llm/03-theoretical-foundations/)

整理 LLM 內部運作機制：[神經網路基礎](/llm/03-theoretical-foundations/neural-network-basics/)、[embedding 空間](/llm/03-theoretical-foundations/embedding-spaces/)、[attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)、[Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)、[訓練流程](/llm/03-theoretical-foundations/training-pipeline/)（pre-train → SFT → RLHF / DPO）、[sampling 策略](/llm/03-theoretical-foundations/sampling-and-decoding/)、[tokenization 算法](/llm/03-theoretical-foundations/tokenization-algorithms/)、[跨語言場景原理](/llm/03-theoretical-foundations/cross-language-tokenization/)。每章末尾接到[公開課推薦](/llm/03-theoretical-foundations/going-deeper-theory/)（Karpathy、Stanford CS224N / CS25 / CS336、DeepLearning.AI）。

### [模組四：LLM 應用層原理](/llm/04-applications/)

整理 LLM 作為系統元件的設計原理：[RAG](/llm/04-applications/rag-principles/)、[tool use](/llm/04-applications/tool-use-principles/)、[agent 架構](/llm/04-applications/agent-architecture/)、[應用層協議](/llm/04-applications/application-protocols/)、[workflow 編排模式](/llm/04-applications/workflow-patterns/)。本模組刻意只寫跨工具世代不變的原理、避開 LangChain / LlamaIndex 等具體 framework 教學。

## 模組之間怎麼配合

| 模組   | 角度             | 跟其他模組的關係                            |
| ------ | ---------------- | ------------------------------------------- |
| 模組零 | 操作層心智模型   | 是模組一的前置                              |
| 模組一 | 工具層、實際安裝 | 用模組零的詞彙、跟模組三的理論互補          |
| 模組二 | 數學工具         | 提供模組三需要的數學詞彙                    |
| 模組三 | 理論機制         | 用模組二的工具拼出完整 LLM                  |
| 模組四 | 應用層原理       | 用前面四個模組建的詞彙、看 LLM 作為系統元件 |

模組二跟模組三可並讀。閱讀模組三遇到陌生數學詞時跳回模組二補完、再回模組三繼續。模組四在前四個模組之上、但讀者熟悉 LLM 應用詞彙也可直接從這裡讀起。

## 適合的讀者

| 背景                                      | 適合程度   | 建議起點                                                                                                                         |
| ----------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 用過 ChatGPT / Claude、沒碰過本地模型     | 直接適合   | [模組零](/llm/00-foundations/) 從頭讀                                                                                            |
| 裝過 Ollama 但被網路上的術語混淆          | 直接適合   | [MLX / MTP / oMLX 區分](/llm/00-foundations/mlx-mtp-omlx/) + [判讀框架](/llm/00-foundations/info-judgment-frames/)               |
| 想知道 24GB / 32GB Mac 該選哪個模型       | 直接適合   | [硬體記憶體預算](/llm/00-foundations/hardware-memory-budget/) + [模型選型](/llm/01-local-llm-services/model-selection-priority/) |
| 想用本地 LLM 完全取代 Claude / GPT-5      | 部分適合   | [期望管理](/llm/01-local-llm-services/expectation-management/) 先看完再決定                                                      |
| 想懂 LLM 內部運作機制                     | 直接適合   | [模組三 理論基礎](/llm/03-theoretical-foundations/) 從頭讀                                                                       |
| 想懂背後的數學                            | 直接適合   | [模組二 數學基礎](/llm/02-math-foundations/) 從頭讀                                                                              |
| 想自己訓練 / fine-tune LLM                | 部分適合   | 讀完模組三後進入 [推薦的公開課程](/llm/03-theoretical-foundations/going-deeper-theory/)                                          |
| 想在 Linux server / NVIDIA GPU 跑推論     | 部分適合   | 本指南的伺服器章節聚焦 Apple Silicon、模組二 / 三 通用；資料中心 inference 教材另尋                                              |
| 想跑 Stable Diffusion / Midjourney 等產圖 | 跟主題不同 | 產圖是 Diffusion 架構、見 [Diffusion 卡片](/llm/knowledge-cards/diffusion/)、另尋 ComfyUI / Draw Things 教材                     |

## 用語約定

本指南使用的關鍵術語在第一次出現時都附原文。為避免歧義，下列詞彙在本指南內固定指涉：

1. **本地 LLM**：跑在使用者自己 Mac 上的大型語言模型推論、prompt 留在本機。
2. **推論伺服器**（inference server）：負責載入模型權重、處理 prompt、產生 token 的常駐程式、例如 Ollama、LM Studio 內建 server、llama.cpp `server`。
3. **介面層**：使用者實際打字互動的工具、例如 VS Code + Continue.dev、CLI、Web UI。介面層透過 API 跟推論伺服器溝通。
4. **模型**（model）：權重檔本身、例如 `gemma4:31b`、`qwen3-coder:30b`。模型可以在不同推論伺服器之間共用、前提是格式相容。
5. **量化**（quantization）：把模型權重從高精度（如 bf16）壓成低精度（如 Q4）以減少記憶體佔用、代價是少許品質下降。

## 不在本指南內的主題

本指南不討論：

- **多模態 LLM**（vision、speech）：跟核心文字 LLM 是不同方向、本指南聚焦文字。
- **資料中心訓練的工程細節**：data parallelism、ZeRO、tensor parallelism 等屬於專門課程的範圍。
- **向量資料庫的選型**（Pinecone、Weaviate、Chroma 比較等）：交給 RAG 專門教材；RAG 設計原理見 [4.0 RAG 原理](/llm/04-applications/rag-principles/)。
- **Kubernetes 上的 LLM 部署**：跟本地 Mac 場景方向不同。

若讀完本指南後想往這些方向走：

1. **想做 [RAG](/llm/knowledge-cards/rag/) 應用**：先把 Ollama + Continue.dev 跑穩、再讀 [模組四 4.0 RAG 原理](/llm/04-applications/rag-principles/) 建立設計取捨判讀、或 [模組三 3.8 推薦](/llm/03-theoretical-foundations/going-deeper-theory/) 的 DeepLearning.AI short courses。
2. **想跑 coding [agent](/llm/knowledge-cards/agent/)**：先讀 [4.2 Agent 架構原理](/llm/04-applications/agent-architecture/) 建立判讀、再看 [1.6 延伸方向](/llm/01-local-llm-services/extension-paths/) 了解 aider、Cline 等工具的定位差異。
3. **想跑產圖模型**：[Diffusion](/llm/knowledge-cards/diffusion/) 跟 Transformer 是不同架構、請另尋 ComfyUI / Draw Things / Diffusers 教材。
4. **想自己訓練 / fine-tune**：讀完模組三、進入 Karpathy zero-to-hero、Stanford CS336、Hugging Face NLP Course 等[推薦資源](/llm/03-theoretical-foundations/going-deeper-theory/)。

---

_文件版本：v0.3.0_
_最後更新：2026-05-11_
_系列狀態：五個模組 + 知識卡片初稿完成（模組四應用層原理為大綱階段）_
