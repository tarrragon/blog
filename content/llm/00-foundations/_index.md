---
title: "模組零：基礎知識與心智模型"
date: 2026-05-11
description: "建立本地 LLM 的心智模型、釐清 MLX / MTP / oMLX 等常被混淆的術語、Apple Silicon 記憶體現實"
tags: ["llm", "foundations", "mac"]
weight: 0
---

本模組的核心目標是把「本地跑 LLM」這件事拆成可討論的工程概念。先建立心智模型再進入工具選擇，可以避開大量網路文章把 framework、加速技巧、伺服器混為一談的陷阱；讀完模組零再進模組一，就能用同一套詞彙判讀任何新的本地 LLM 工具是在解哪一層的問題。

讀完本模組後，你應該能清楚回答：本地跟雲端跑 LLM 的差別在哪、為什麼 LLM 一個字一個字吐而不是整段吐、什麼是介面 / 伺服器 / 模型三層架構、為何 OpenAI 相容 API 是整個生態的基石、MLX 跟 MTP 跟 oMLX 各自是什麼東西、自己這台 Mac 的記憶體能跑多大的模型。

## 章節列表

| 章節                                                 | 主題                         | 關鍵收穫                                                    |
| ---------------------------------------------------- | ---------------------------- | ----------------------------------------------------------- |
| [0.0](/llm/00-foundations/local-vs-cloud/)           | 本地 vs 雲端 LLM             | 從隱私、成本、速度、能力四個維度建立基本對照                |
| [0.1](/llm/00-foundations/why-llm-feels-slow/)       | 為什麼 LLM 生字慢            | 自回歸架構 + 記憶體頻寬瓶頸：一次只能吐一個 token           |
| [0.2](/llm/00-foundations/three-layer-architecture/) | 介面 / 伺服器 / 模型三層架構 | 把任何本地 LLM 工具放回正確的層級，看懂工具關係             |
| [0.3](/llm/00-foundations/openai-compatible-api/)    | OpenAI 相容 API              | 為什麼幾乎所有工具不用改就能切到本地：背後是同一套 API 形狀 |
| [0.4](/llm/00-foundations/mlx-mtp-omlx/)             | MLX / MTP / oMLX 的區別      | 三者疊加而非互斥：framework、加速技巧、特化 server          |
| [0.5](/llm/00-foundations/hardware-memory-budget/)   | Apple Silicon 記憶體預算     | 記憶體決定能跑什麼，Q4 量化下的可運作模型對照與系統保留     |
| [0.6](/llm/00-foundations/info-judgment-frames/)     | 判讀本地 LLM 資訊的五個框架  | 版本時間、量化變數、三層架構、載入 vs 好用、隱私資料流      |
| [0.7](/llm/00-foundations/privacy-data-flow/)        | 隱私 / 資安的資料流原理      | 從「位置」到「資料流」思考、信任邊界、零信任原則            |
| [0.8](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) | Deterministic vs Fuzzy Engineering 典範 | 兩個典範的四維對照、guardrail 設計、跟 agent / workflow 的關係 |

## 為什麼先讀模組零

模組一的安裝步驟看起來只是 `brew install` 加一行 `ollama run`，但每個指令背後都隱含選擇：要選哪個推論伺服器、要拉哪個量化等級的模型、要不要打開 speculative decoding、API 接哪個 port。若沒有模組零的心智模型，這些選擇只能靠抄文章上的指令，遇到變化就無法判讀。

例如網路上常見的「裝完 Ollama 就能用 MLX 加速」這種說法，背後混淆了三件事：Ollama 是不是用 MLX 當 backend、MLX 跟 Metal 在 Apple Silicon 上的關係、加速來自 MLX 還是 MTP 還是量化。讀完 [0.4](/llm/00-foundations/mlx-mtp-omlx/) 後你會自然知道這句話該怎麼追問才能得到正確答案。

## 模組零的閱讀策略

本模組八篇章節彼此獨立，但建議依下列順序讀：

1. 先讀 [0.0 本地 vs 雲端](/llm/00-foundations/local-vs-cloud/) 跟 [0.1 為什麼 LLM 生字慢](/llm/00-foundations/why-llm-feels-slow/)，建立「本地 LLM 解什麼問題、不解什麼問題」的判斷。
2. 接著讀 [0.2 三層架構](/llm/00-foundations/three-layer-architecture/) 跟 [0.3 OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)，建立「工具如何拼裝」的判斷。
3. 然後讀 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)，避開最常見的術語陷阱。
4. 接著讀 [0.5 硬體記憶體](/llm/00-foundations/hardware-memory-budget/) 跟 [0.6 判讀框架](/llm/00-foundations/info-judgment-frames/)、把心智模型對到自己手上這台 Mac 的現實、並建立評估新資訊的反射。
5. 讀 [0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/)、把 0.6 框架五展開成可操作的設計原則。
6. 最後讀 [0.8 Deterministic vs Fuzzy Engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)、建立「LLM 軟體跟傳統軟體的設計典範差異」心智模型、為進入[模組四 LLM 應用層](/llm/04-applications/) 做準備。

讀完後可進 [模組一：本地 LLM 服務的安裝與應用](/llm/01-local-llm-services/) 看安裝步驟、或直接進 [模組四 LLM 應用層](/llm/04-applications/) 看典範怎麼落到 RAG / agent / workflow 設計。

## 不在本模組內的主題

本模組聚焦「操作層心智模型」、其他層次交給對應模組：

1. **Transformer 架構數學細節**（attention、positional encoding、residual stream 等）→ [模組三 LLM 理論基礎](/llm/03-theoretical-foundations/)
2. **線性代數、機率、最佳化、數值精度等數學工具** → [模組二 數學基礎](/llm/02-math-foundations/)
3. **訓練、fine-tuning、RLHF、DPO** → [模組三 3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)
4. **具體工具的安裝步驟** → [模組一 本地 LLM 服務](/llm/01-local-llm-services/)
5. **雲端 GPU 部署** → 本指南範圍只在 Apple Silicon Mac、請另尋資料中心 inference 教材

本模組只提供「Mac 本地寫 code」這條最短路徑需要的概念基底；其他層次的學習路線見[首頁的模組對照表](/llm/)。
