---
title: "模組四：LLM 應用層原理"
date: 2026-05-11
description: "RAG、tool use、agent、應用層協議、workflow 編排：跨工具不變的概念地圖"
tags: ["llm", "applications", "rag", "tool-use", "agent", "mcp"]
weight: 4
---

> **狀態**：大綱階段、待完成內容。

本模組整理 LLM 應用層的核心原理：模型裝起來、能對話之後、要怎麼跟外部世界互動、怎麼組成可用的工作流。模組零到模組三建立的是「模型本身」的心智模型；本模組建立的是「模型作為系統元件」的心智模型。

寫這個模組的核心約束是「**只寫不會過時的部分**」。LangChain、LlamaIndex、aider、Cline 等工具半年一個世代、寫具體 API 半年後就過時；但「retrieval 在做什麼」「為什麼 LLM 需要 tool use」「agent loop 為什麼會失敗」這些原理跨工具世代都成立。本模組刻意避開具體實作教學、把焦點放在跨世代的設計取捨。

## 章節列表

| 章節                                                      | 主題                                                   | 關鍵收穫                                                                                                      |
| --------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| [4.0](/llm/04-applications/rag-principles/)               | RAG 原理：retrieval + augmentation 模式                | 為什麼要外掛知識、語意相似 vs 字面相似、chunking 取捨、失敗的根本原因                                         |
| [4.1](/llm/04-applications/tool-use-principles/)          | Tool use 原理：LLM 跟外部世界互動                      | structured output 是橋、function calling 取捨、為什麼小模型 tool use 崩                                       |
| [4.2](/llm/04-applications/agent-architecture/)           | Agent 架構原理                                         | Agent loop 結構、失敗模式、什麼任務適合 vs 不適合、人類審查模型                                               |
| [4.3](/llm/04-applications/application-protocols/)        | 應用層協議：function calling / structured output / MCP | 三者層級差異、為什麼出現 MCP、組合工作流                                                                      |
| [4.4](/llm/04-applications/workflow-patterns/)            | Workflow 編排模式                                      | Pipeline / router / parallel / reflection 四種基本模式、退化條件                                              |
| [4.5](/llm/04-applications/production-resource-planning/) | Production 部署的資源評估原理                          | 6 個 dimension：concurrency / latency / cost / storage / observability / reliability                          |
| [4.6](/llm/04-applications/artifact-management/)          | 衍生產物管理原理：什麼進 git、什麼不該                 | Source / derived / external 三分類、`.gitignore` 設計模式、prompt + eval 版本管理、production deployment 對接 |

## 為什麼這個順序

本模組章節順序的設計脈絡：

1. **先 4.0 RAG**：應用層最常見的模式、把「LLM + 外部知識」這個基本組合走過一遍、概念對映到每個讀者都用過的 `@codebase` 等實務經驗。
2. **再 4.1 Tool use**：RAG 是「LLM 讀外部資料」、Tool use 是「LLM 對外部世界做事」、兩條延伸方向自然接續。
3. **接 4.2 Agent 架構**：把 Tool use 從「單次呼叫」延伸到「自主多步」、自然進入 agent。
4. **再 4.3 應用層協議**：前面三章涉及 function calling、structured output、MCP 等術語、本章把這三個概念放回正確的層級、避免混為一談。
5. **最後 4.4 Workflow 編排模式**：上層整合、把多 LLM call 組合的設計模式整理成跨 framework 不變的概念地圖。

每章可以單獨讀、但若你是第一次接觸 LLM 應用層、照順序讀最不容易迷路。

## 跟其他模組的分工

| 模組   | 角度                                                       |
| ------ | ---------------------------------------------------------- |
| 模組零 | 操作層心智模型：模型放哪、怎麼選工具                       |
| 模組一 | 工具層：具體裝 Ollama / Continue.dev                       |
| 模組二 | 數學工具：線性代數、機率、最佳化                           |
| 模組三 | 理論機制：模型內部運作                                     |
| 模組四 | **應用層原理**：模型作為系統元件、跟外部世界互動的設計取捨 |

## 適合的讀者

| 你的背景                                     | 適合程度                                     |
| -------------------------------------------- | -------------------------------------------- |
| 寫過 Ollama + Continue.dev、想懂「然後呢」   | 直接適合、從 4.0 依序讀                      |
| 已經試過 LangChain / aider / Cline、想看原理 | 直接適合、本模組補足「為什麼這樣設計」的視角 |
| 想做 LLM 應用開發                            | 重點讀 4.0、4.1、4.3、4.4                    |
| 只想用本地 LLM 寫 code、不做應用             | 跳過本模組無妨、模組零 + 模組一已足夠        |

## 不在本模組內的主題

1. **具體 framework 教學**：LangChain、LlamaIndex 等的 API 用法、隨版本變、交給官方文件。
2. **Prompt engineering**：太客製化、每個模型每個場景都不同、不寫進長期教材。
3. **具體 agent 工具配置**：aider、Cline 等的安裝設定、隨工具版本變、見 [1.6 延伸方向](/llm/01-local-llm-services/extension-paths/) 的入口資訊。
4. **訓練 / fine-tuning**：屬於改變模型本身、見 [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)。
