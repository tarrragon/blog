---
title: "LLM 寫 code 工程實務指南：從心智模型到應用架構"
date: 2026-05-12
description: "以寫 code 場景為主、涵蓋本地推論（Mac / PC）、雲端混用、LLM 數學與理論基礎、應用層架構（RAG / tool use / agent / VLM / 靜態 deployment）、reasoning model 與 speculative decoding、本地 dev 安全、跨工具世代不變的原理"
tags: ["llm", "local-llm", "mac", "apple-silicon", "nvidia", "discrete-gpu", "windows", "linux", "ollama", "llama-cpp", "foundations", "transformer", "inference", "rag", "agent", "vlm", "reasoning", "security", "deployment"]
weight: 36
---

本指南的核心目標是把「LLM 在寫 code 工作流的完整工程地圖」拆成可決策、可實作、可期望管理的工程問題。範圍覆蓋四條讀者旅程：(1) 在自己機器跑本地 LLM 寫 code 的最短可行路徑（Mac 或 PC）、(2) 想懂 LLM 內部運作機制（數學 + 理論基礎）、(3) 想做 LLM 應用開發（RAG / agent / tool use / VLM / benchmarking / 靜態 deployment）、(4) 關心 LLM 工作流的安全議題（本地 dev 視角 + 靜態網站視角）。網路上的 LLM 文章常把推論框架、加速技巧、應用模式、安全議題混為一談；本指南先把這些名詞放回正確的層級、再回答各層的具體取捨。

本指南預設讀者已經會用過雲端 LLM（ChatGPT、Claude）、熟悉終端機操作、想以工程視角理解 LLM。**寫 code 場景是主要使用例、但模組二 / 三 / 四 / 六多數章節跨場景通用**：想懂 reasoning model / RAG / embedding model 內部、即使不裝本地 LLM 也能讀。硬體前提分兩條路線：Apple Silicon Mac（M1 ~ M4、統一記憶體）走模組一；Windows / Linux + 獨立 GPU（NVIDIA / AMD、獨立 VRAM + 系統 RAM）走模組五。文章不販賣 LLM 焦慮、也不誇大本地能取代雲端的程度；它的責任是給每條讀者旅程的最短可行路徑、並標出每個階段的取捨。

模組零（心智模型）是所有讀者旅程的共同前置。模組一跟模組五是「裝本地 LLM」的兩條硬體路線、依平台選一條；想懂底層走模組二跟模組三（跟硬體無關、含 reasoning model / speculative decoding 等推論細節）；想看 LLM 作為系統元件走模組四（12 章涵蓋 RAG、tool use、agent、應用層協議、workflow、production resource、long context、embedding model、benchmarking、vision、靜態 deployment）；本地工作流跑穩想看安全議題走模組六（個人 dev 視角的供應鏈、伺服器綁定、tool use 權限、prompt injection、跨雲端邊界、production routing）。

## 教材邊界

| 類型           | 放在本指南                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 不放在本指南                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 心智模型       | 本地 vs 雲端的差異、為何 LLM 生字慢、三層架構（介面 / 伺服器 / 模型）、[OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)                                                                                                                                                                                                                                                                                                                                                                                                                                      | 雲端 GPU 租用、AGI 預測                                           |
| 術語澄清       | [MLX](/llm/00-foundations/mlx-mtp-omlx/)、[MTP](/llm/00-foundations/mlx-mtp-omlx/)、[oMLX](/llm/00-foundations/mlx-mtp-omlx/)、[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[量化](/llm/knowledge-cards/quantization/)、[KV cache](/llm/knowledge-cards/kv-cache/)、[TTFT](/llm/knowledge-cards/ttft/)、[MoE CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/)                                                                                                                                                                                      | post-training fine-tuning 細節                                    |
| Mac 硬體現實   | [記憶體預算與模型大小](/llm/00-foundations/hardware-memory-budget/)、量化選擇、首字延遲、風扇與功耗                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 雲端 GPU 租用、資料中心訓練                                       |
| PC 硬體現實    | [VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/)、MoE 專家層 CPU 卸載、KV cache 量化、PCIe 頻寬限制                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 多卡 NVLink、資料中心級分散式推論                                 |
| 本地推論伺服器 | [Ollama](/llm/01-local-llm-services/ollama/)、[LM Studio](/llm/01-local-llm-services/lm-studio/)、[llama.cpp](/llm/01-local-llm-services/llama-cpp/)（Mac + PC 通用）                                                                                                                                                                                                                                                                                                                                                                                                     | vLLM、TGI、Triton 等資料中心級 inference server                   |
| 編輯器整合     | [Continue.dev + VS Code](/llm/01-local-llm-services/vscode-continue-integration/)、Cursor 對應關係                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | JetBrains 全套整合、Vim / Emacs 進階 plugin                       |
| 模型挑選       | [coding 場景的模型優先順序](/llm/01-local-llm-services/model-selection-priority/)、量化等級對體感影響                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | benchmark 跑分方法論的完整推導                                    |
| 期望管理       | [本地 LLM 的擅長領域與分工](/llm/01-local-llm-services/expectation-management/)、混用雲端的時機                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | LLM 通用能力評估、AGI 預測                                        |
| 數學基礎       | [線性代數](/llm/02-math-foundations/linear-algebra-for-llm/)、[機率與資訊論](/llm/02-math-foundations/probability-and-information/)、[最佳化](/llm/02-math-foundations/calculus-and-optimization/)、[數值精度](/llm/02-math-foundations/numerical-precision/) 在 LLM 中的角色                                                                                                                                                                                                                                                                                             | 完整數學證明、測度論等屬於數學系範圍的主題                        |
| 理論基礎       | [神經網路](/llm/03-theoretical-foundations/neural-network-basics/)、[embedding](/llm/03-theoretical-foundations/embedding-spaces/)、[attention](/llm/03-theoretical-foundations/attention-mechanism/)、[Transformer](/llm/03-theoretical-foundations/transformer-architecture/)、[訓練流程](/llm/03-theoretical-foundations/training-pipeline/)、[sampling](/llm/03-theoretical-foundations/sampling-and-decoding/)、[tokenization](/llm/03-theoretical-foundations/tokenization-algorithms/)、[跨語言原理](/llm/03-theoretical-foundations/cross-language-tokenization/) | 多模態擴展、最新研究細節交給 Stanford CS25                        |
| 應用層原理     | [RAG](/llm/04-applications/rag-principles/)、[Tool use](/llm/04-applications/tool-use-principles/)、[Agent 架構](/llm/04-applications/agent-architecture/)、[應用層協議](/llm/04-applications/application-protocols/)、[Workflow 編排](/llm/04-applications/workflow-patterns/)、[Production resource](/llm/04-applications/production-resource-planning/)、[Artifact 管理](/llm/04-applications/artifact-management/)                                                                                                                                                    | 具體 framework 教學（LangChain / LlamaIndex）、prompt engineering |
| 進階理論       | [Reasoning models](/llm/03-theoretical-foundations/reasoning-models/)（o1 / R1 / QwQ 風格）、[Speculative decoding 內部](/llm/03-theoretical-foundations/speculative-decoding-internals/)（drafter / MTP / EAGLE）                                                                                                                                                                                                                                                                                                                                                        | 完整 paper 推導、最新研究 frontier                                |
| 進階應用       | [Long context engineering](/llm/04-applications/long-context-engineering/)、[Embedding model 內部](/llm/04-applications/embedding-model-internals/)、[Benchmarking](/llm/04-applications/benchmarking-and-evaluation/)、[Vision in coding](/llm/04-applications/vision-in-coding-workflow/)、[靜態 / serverless RAG deployment](/llm/04-applications/static-and-serverless-rag-deployment/)                                                                                                                                                                               | 完整 LangChain / LlamaIndex 教學                                  |
| Fine-tuning    | 原理（[LoRA](/llm/knowledge-cards/lora/) / [QLoRA](/llm/knowledge-cards/qlora/) / [catastrophic forgetting](/llm/knowledge-cards/catastrophic-forgetting/)）+ [本機 hands-on](/llm/01-local-llm-services/hands-on/local-fine-tuning/)                                                                                                                                                                                                                                                                                                                                     | 完整資料工程、large-scale distributed fine-tune                   |
| 隱私 / 安全    | [隱私資料流](/llm/00-foundations/privacy-data-flow/)、[本地 dev 安全模組](/llm/06-security/)（供應鏈 / 伺服器綁定 / tool use / prompt injection / 跨雲端邊界 / production routing）、[靜態網站 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/)、[排錯方法論](/llm/01-local-llm-services/troubleshooting/)                                                                                                                                                                                                                                           | 企業合規逐條檢核、SOC 2 / HIPAA 流程                              |
| 進一步學習     | [數學公開課推薦](/llm/02-math-foundations/going-deeper-math/)、[LLM 理論公開課推薦](/llm/03-theoretical-foundations/going-deeper-theory/)                                                                                                                                                                                                                                                                                                                                                                                                                                 | （交給推薦的課程跟書籍）                                          |

## 學習路線

本指南分成七個模組加一組前置卡片（111 張）。讀者依目的選讀、不需要從頭到尾全讀：

- **想用 Apple Silicon Mac 裝本地 LLM 寫 code**：讀模組零 + 模組一（最短路徑）
- **想用 Windows / Linux + 獨立 GPU 裝**：讀模組零 + 模組五
- **想懂 LLM 內部原理**：模組二（數學） + 模組三（理論、含 reasoning models / speculative decoding）— 跟硬體無關
- **想做 LLM 應用開發（含 RAG / agent / VLM / 靜態 deployment）**：模組四（12 章、跨工具世代不變的原理）— 跟硬體無關
- **想懂本地工作流的安全議題**：模組一 / 五跑穩後接模組六（個人 dev 視角）
- **想選 RAG 的 storage 方案（pickle / vector DB / hosted SaaS）**：直接看 [4.22 RAG storage 工程](/llm/04-applications/vector-storage-engineering/)
- **想在靜態網站加 RAG / 智能搜尋**：直接看 [4.16 靜態 / serverless RAG deployment](/llm/04-applications/static-and-serverless-rag-deployment/)
- **想在本機 fine-tune 模型**：模組三 3.4 訓練流程原理 → [本機 QLoRA hands-on](/llm/01-local-llm-services/hands-on/local-fine-tuning/)
- **想跟最新進展接軌**：讀完模組後進推薦的公開課程跟 paper（模組二 2.4 + 模組三 3.10）

### [前置知識卡片](/llm/knowledge-cards/)

用原子化卡片整理 [token](/llm/knowledge-cards/token/)、[自回歸](/llm/knowledge-cards/autoregressive/)、[KV cache](/llm/knowledge-cards/kv-cache/)、[量化](/llm/knowledge-cards/quantization/)、[speculative decoding](/llm/knowledge-cards/speculative-decoding/)、[MTP](/llm/knowledge-cards/mtp/)、[MLX](/llm/knowledge-cards/mlx/)、[推論伺服器](/llm/knowledge-cards/inference-server/)、[OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)、[memory bandwidth](/llm/knowledge-cards/memory-bandwidth/)、[統一記憶體](/llm/knowledge-cards/unified-memory/)、[TTFT](/llm/knowledge-cards/ttft/)、[prefill](/llm/knowledge-cards/prefill/)、[context window](/llm/knowledge-cards/context-window/)、[Transformer](/llm/knowledge-cards/transformer/)、[Diffusion](/llm/knowledge-cards/diffusion/) 等核心概念。章節文章專注情境推導、術語背景交由卡片維持一致。

### [模組零：基礎知識與心智模型](/llm/00-foundations/)

整理本地 vs 雲端 LLM 的差異、自回歸架構與記憶體頻寬瓶頸、介面 / 伺服器 / 模型三層心智模型、OpenAI 相容 API 為何重要、MLX / MTP / oMLX 三個容易搞混的術語、Apple Silicon Mac 記憶體與模型大小的對應關係、判讀本地 LLM 資訊的五個框架。

### [模組一：本地 LLM 服務的安裝與應用](/llm/01-local-llm-services/)

整理 Ollama、LM Studio、llama.cpp 三個主流推論伺服器的現況差異與安裝路徑、用 Continue.dev 把本地 LLM 接到 VS Code 的完整步驟、寫 code 場景下模型選型的優先順序、本地模型的期望管理、想進一步玩 coding agent、Web UI、產圖時的延伸方向。

### [模組二：LLM 的數學基礎](/llm/02-math-foundations/)

整理 LLM 推論背後的數學工具：[線性代數](/llm/02-math-foundations/linear-algebra-for-llm/)（向量、矩陣、空間）、[機率與資訊論](/llm/02-math-foundations/probability-and-information/)（softmax、cross-entropy、KL、perplexity）、[微積分與最佳化](/llm/02-math-foundations/calculus-and-optimization/)（gradient、SGD / Adam）、[數值精度](/llm/02-math-foundations/numerical-precision/)（fp32 / bf16 / Q4 / Q8 的取捨）。每章末尾接到[公開課推薦](/llm/02-math-foundations/going-deeper-math/)。

### [模組三：LLM 的理論基礎](/llm/03-theoretical-foundations/)

整理 LLM 內部運作機制、共 11 章：[神經網路基礎](/llm/03-theoretical-foundations/neural-network-basics/)、[embedding 空間](/llm/03-theoretical-foundations/embedding-spaces/)、[attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)、[Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)、[訓練流程](/llm/03-theoretical-foundations/training-pipeline/)（pre-train → SFT → RLHF / DPO）、[sampling 策略](/llm/03-theoretical-foundations/sampling-and-decoding/)、[tokenization 算法](/llm/03-theoretical-foundations/tokenization-algorithms/)、[跨語言場景原理](/llm/03-theoretical-foundations/cross-language-tokenization/)、[Reasoning models](/llm/03-theoretical-foundations/reasoning-models/)（o1 / R1 / QwQ 等 test-time compute paradigm）、[Speculative decoding 內部](/llm/03-theoretical-foundations/speculative-decoding-internals/)（drafter / MTP / EAGLE）。每章末尾接到[公開課推薦](/llm/03-theoretical-foundations/going-deeper-theory/)（Karpathy、Stanford CS224N / CS25 / CS336、DeepLearning.AI）。

### [模組四：LLM 應用層原理](/llm/04-applications/)

整理 LLM 作為系統元件的設計原理、共 12 章：[RAG](/llm/04-applications/rag-principles/)、[tool use](/llm/04-applications/tool-use-principles/)、[agent 架構](/llm/04-applications/agent-architecture/)、[應用層協議](/llm/04-applications/application-protocols/)、[workflow 編排模式](/llm/04-applications/workflow-patterns/)、[Production resource planning](/llm/04-applications/production-resource-planning/)、[衍生產物管理](/llm/04-applications/artifact-management/)、[Long context engineering](/llm/04-applications/long-context-engineering/)、[Embedding model 內部](/llm/04-applications/embedding-model-internals/)、[Benchmarking 方法論](/llm/04-applications/benchmarking-and-evaluation/)、[Vision in coding workflow](/llm/04-applications/vision-in-coding-workflow/)（本地 VLM 接 IDE）、[靜態 / serverless RAG deployment](/llm/04-applications/static-and-serverless-rag-deployment/)（沒 backend 場景）。本模組刻意只寫跨工具世代不變的原理、避開 LangChain / LlamaIndex 等具體 framework 教學。

### [模組五：Windows / Linux + 獨立 GPU](/llm/05-discrete-gpu/)

整理消費級 PC（Windows / Linux + NVIDIA / AMD 獨立 GPU）跑本地 LLM 的硬體判讀模型與工程選項：[VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/)、MoE 模型的 [CPU 卸載策略](/llm/knowledge-cards/moe-cpu-offload/)（`--n-cpu-moe`）、KV cache 量化（K=Q8 / V=Q4）跟 context 長度的權衡、llama.cpp 在 PC 上的調參空間。本模組跟模組一是平行的硬體路線、共用模組零的心智模型跟卡片。

### [模組六：本地 LLM 的安全與權限](/llm/06-security/)

整理個人 dev 在自己機器上跑本地 LLM 的安全議題：[模型供應鏈與信任邊界](/llm/06-security/model-supply-chain-trust/)、[推論伺服器的綁定與暴露範圍](/llm/06-security/inference-server-binding/)、[tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)、[IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)、[跨雲端 / 本地的資料邊界](/llm/06-security/cross-cloud-local-data-boundary/)、[跨進 production 的 routing 中樞](/llm/06-security/routing-to-production-security/)。framing 是個人 dev 視角、不是 enterprise 資安管理；production / 多租戶 LLM 服務的特殊資安議題見 [Backend 模組七 資安與資料保護](/backend/07-security-data-protection/) 的 LLM 相關章節。

## 模組之間怎麼配合

| 模組   | 角度                  | 跟其他模組的關係                                                      |
| ------ | --------------------- | --------------------------------------------------------------------- |
| 模組零 | 操作層心智模型        | 是模組一跟模組五的共同前置                                            |
| 模組一 | 工具層、Mac 實際安裝  | 用模組零的詞彙、跟模組三的理論互補                                    |
| 模組二 | 數學工具              | 提供模組三需要的數學詞彙、跟硬體平台無關                              |
| 模組三 | 理論機制              | 用模組二的工具拼出完整 LLM、跟硬體平台無關                            |
| 模組四 | 應用層原理            | 用前面模組建的詞彙、看 LLM 作為系統元件                               |
| 模組五 | 工具層、PC 獨立 GPU   | 跟模組一平行、用模組零的詞彙、處理 VRAM 場景                          |
| 模組六 | 安全層、個人 dev 視角 | 在模組一 / 五的工作流上加安全判讀、cross-link backend/07 通用資安卡片 |

模組二跟模組三可並讀。閱讀模組三遇到陌生數學詞時跳回模組二補完、再回模組三繼續。模組四在前面模組之上、但讀者熟悉 LLM 應用詞彙也可直接從這裡讀起。模組一跟模組五依硬體選一條主路線、共用模組零的心智模型與 [knowledge-cards](/llm/knowledge-cards/)。模組六在模組一 / 五跑穩後接、處理「跑起來後該注意什麼」。

## 適合的讀者

| 背景                                                  | 適合程度   | 建議起點                                                                                                                                           |
| ----------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用過 ChatGPT / Claude、沒碰過本地模型                 | 直接適合   | [模組零](/llm/00-foundations/) 從頭讀                                                                                                              |
| 裝過 Ollama 但被網路上的術語混淆                      | 直接適合   | [MLX / MTP / oMLX 區分](/llm/00-foundations/mlx-mtp-omlx/) + [判讀框架](/llm/00-foundations/info-judgment-frames/)                                 |
| 想知道 24GB / 32GB Mac 該選哪個模型                   | 直接適合   | [硬體記憶體預算](/llm/00-foundations/hardware-memory-budget/) + [模型選型](/llm/01-local-llm-services/model-selection-priority/)                   |
| 想用本地 LLM 完全取代 Claude / GPT-5                  | 部分適合   | [期望管理](/llm/01-local-llm-services/expectation-management/) 先看完再決定                                                                        |
| 想懂 LLM 內部運作機制                                 | 直接適合   | [模組三 理論基礎](/llm/03-theoretical-foundations/) 從頭讀（含 reasoning models / speculative decoding）                                           |
| 想懂背後的數學                                        | 直接適合   | [模組二 數學基礎](/llm/02-math-foundations/) 從頭讀                                                                                                |
| 想懂 o1 / DeepSeek-R1 等 reasoning model 怎麼運作     | 直接適合   | [3.8 Reasoning models](/llm/03-theoretical-foundations/reasoning-models/) 從頭讀                                                                   |
| 想做 LLM 應用開發（RAG / agent / tool use）           | 直接適合   | [模組四](/llm/04-applications/) 從 4.0 RAG 依序讀                                                                                                  |
| 想在自家 Hugo / Astro 等靜態網站加 RAG                | 直接適合   | [4.16 靜態 / serverless RAG deployment](/llm/04-applications/static-and-serverless-rag-deployment/)（含資安取捨）                                  |
| 想用 VLM 看截圖 / 設計稿輔助寫 code                   | 直接適合   | [4.15 Vision in coding workflow](/llm/04-applications/vision-in-coding-workflow/)                                                                  |
| 想評估 LLM benchmark 數字、做 in-house eval           | 直接適合   | [4.14 Benchmarking 方法論](/llm/04-applications/benchmarking-and-evaluation/)                                                                      |
| 想在本機 fine-tune 模型懂自家 codebase 慣例           | 直接適合   | [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/) 原理 + [QLoRA hands-on](/llm/01-local-llm-services/hands-on/local-fine-tuning/) |
| 想做 large-scale fine-tune / 從頭訓練                 | 部分適合   | 讀完模組三後進入 [推薦的公開課程](/llm/03-theoretical-foundations/going-deeper-theory/) 跟 Stanford CS336                                          |
| 用 Windows / Linux + NVIDIA / AMD 獨立 GPU 跑本地 LLM | 直接適合   | [模組零](/llm/00-foundations/) 建心智模型 + [模組五](/llm/05-discrete-gpu/) 處理 VRAM 預算、MoE 卸載、KV cache 量化                                |
| 想知道本地 LLM 跑起來後的安全議題                     | 直接適合   | [模組六](/llm/06-security/) 個人 dev 視角的安全與權限                                                                                              |
| 想把 LLM 部署成 production 服務、處理服務化資安       | 部分適合   | 個人視角見 [模組六](/llm/06-security/)；production 場景見 [Backend 模組七 資安](/backend/07-security-data-protection/) 的 LLM 相關章節             |
| 想在資料中心級 GPU（H100 / H200 / B200）部署          | 部分適合   | 心智模型跟 [knowledge-cards](/llm/knowledge-cards/) 通用；vLLM / TGI / Triton 等資料中心 inference server 另尋專門教材                             |
| 想跑 Stable Diffusion / Midjourney 等產圖             | 跟主題不同 | 產圖是 Diffusion 架構、見 [Diffusion 卡片](/llm/knowledge-cards/diffusion/)、另尋 ComfyUI / Draw Things 教材                                       |

## 用語約定

本指南使用的關鍵術語在第一次出現時都附原文。為避免歧義，下列詞彙在本指南內固定指涉：

1. **本地 LLM**：跑在使用者自己機器（Mac 或 PC）上的大型語言模型推論、prompt 留在本機。
2. **推論伺服器**（inference server）：負責載入模型權重、處理 prompt、產生 token 的常駐程式、例如 Ollama、LM Studio 內建 server、llama.cpp `server`。
3. **介面層**：使用者實際打字互動的工具、例如 VS Code + Continue.dev、CLI、Web UI。介面層透過 API 跟推論伺服器溝通。
4. **模型**（model）：權重檔本身、例如 `gemma4:31b`、`qwen3-coder:30b`。模型可以在不同推論伺服器之間共用、前提是格式相容。
5. **量化**（quantization）：把模型權重從高精度（如 bf16）壓成低精度（如 Q4）以減少記憶體佔用、代價是少許品質下降。

## 不在本指南內的主題

本指南不討論：

- **Speech / audio LLM**：跟核心文字 LLM 是不同方向、本指南不涵蓋。Vision（VLM）原本不放、但因 coding 工作流的 vision use case 進入主流、補上 [4.15 Vision in coding workflow](/llm/04-applications/vision-in-coding-workflow/)；video LLM 仍不放。
- **資料中心訓練的工程細節**：data parallelism、ZeRO、tensor parallelism 等屬於專門課程的範圍。
- **向量資料庫的 vendor 比較**（Pinecone vs Weaviate vs Chroma 等）：vendor 格局半年一變、不適合寫入教材。RAG 的 storage 工程原理（升級判讀、index 生命週期、dependency 約束）見 [4.22 RAG storage 工程](/llm/04-applications/vector-storage-engineering/)。
- **Kubernetes / 資料中心級分散式推論**：跟個人機器本地 LLM 方向不同、需另尋專門教材。
- **多卡 NVLink、tensor parallelism**：消費級 PC 場景通常單卡、本指南不涵蓋多卡分散式推論。

若讀完本指南後想往這些方向走：

1. **想做 [RAG](/llm/knowledge-cards/rag/) 應用**：先把 Ollama + Continue.dev 跑穩、再讀 [模組四 4.1 RAG 原理](/llm/04-applications/rag-principles/) 建立設計取捨判讀、或 [模組三 3.8 推薦](/llm/03-theoretical-foundations/going-deeper-theory/) 的 DeepLearning.AI short courses。
2. **想跑 coding [agent](/llm/knowledge-cards/agent/)**：先讀 [4.4 Agent 架構原理](/llm/04-applications/agent-architecture/) 建立判讀、再看 [1.6 延伸方向](/llm/01-local-llm-services/extension-paths/) 了解 aider、Cline 等工具的定位差異。
3. **想跑產圖模型**：[Diffusion](/llm/knowledge-cards/diffusion/) 跟 Transformer 是不同架構、請另尋 ComfyUI / Draw Things / Diffusers 教材。
4. **想自己訓練 / fine-tune**：讀完模組三、進入 Karpathy zero-to-hero、Stanford CS336、Hugging Face NLP Course 等[推薦資源](/llm/03-theoretical-foundations/going-deeper-theory/)。

---

_文件版本：v0.7.0_
_最後更新：2026-05-12_
_系列狀態：七個模組 + 125 張知識卡片。模組零（9 章）/ 一（10 章 + hands-on、含 QLoRA + judge harness）/ 二（5 章）/ 三（12 章、含 reasoning / speculative / constrained decoding）/ 四（17 章、含 long context / embedding / benchmarking / VLM / 靜態 deployment / coding agent harness / prompt caching / agent memory / tracing / LLM-as-judge）/ 五（7 章）/ 六（7 章、含 OWASP 對照）。_
