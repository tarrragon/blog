---
title: "模組四：LLM 應用層原理"
date: 2026-05-14
description: "Prompt 技術光譜、RAG、tool use、agent、應用層協議、人機協作、multi-agent、workflow 編排、eval 設計：跨工具不變的概念地圖"
tags: ["llm", "applications", "rag", "tool-use", "agent", "mcp", "eval"]
weight: 4
---

> **狀態**：大綱階段、部分章節待完成內容。

本模組整理 LLM 應用層的核心原理：模型裝起來、能對話之後、要怎麼跟外部世界互動、怎麼組成可用的工作流、怎麼測它跑得對不對。模組零到模組三建立的是「模型本身」的心智模型；本模組建立的是「模型作為系統元件」的心智模型。

寫這個模組的核心約束是「**只寫不會過時的部分**」。LangChain、LlamaIndex、aider、Cline 等工具半年一個世代、寫具體 API 半年後就過時；但「retrieval 在做什麼」「為什麼 LLM 需要 tool use」「agent loop 為什麼會失敗」「eval 軸怎麼選」這些原理跨工具世代都成立。本模組刻意避開具體實作教學、把焦點放在跨世代的設計取捨。

## 章節列表

| 章節                                                               | 主題                                                   | 關鍵收穫                                                                                                      |
| ------------------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| [4.0](/llm/04-applications/prompt-techniques-landscape/)           | Prompt 技術光譜                                        | 三軸（context / 推理 / 格式）+ 四維 trade-off + stack 判讀 + 跟 fine-tune/RAG/chaining 的邊界                  |
| [4.1](/llm/04-applications/rag-principles/)                        | RAG 原理：retrieval + augmentation 模式                | 為什麼要外掛知識、語意相似 vs 字面相似、chunking 取捨、失敗的根本原因                                         |
| [4.2](/llm/04-applications/rag-retrieval-enhancements/)            | RAG 檢索增強：query rewriting / HyDE / multi-step / packing | 四層增強分類、何時 stack 何時不要、adaptive retrieval                                                          |
| [4.3](/llm/04-applications/tool-use-principles/)                   | Tool use 原理：LLM 跟外部世界互動                      | structured output 是橋、function calling 取捨、為什麼小模型 tool use 崩                                       |
| [4.4](/llm/04-applications/agent-architecture/)                    | Agent 架構原理                                         | Agent loop 結構、失敗模式、什麼任務適合 vs 不適合、人類審查模型                                               |
| [4.5](/llm/04-applications/human-ai-collaboration/)                | 人機協作拓樸：何時人介入、怎麼介入                     | Centaur vs Cyborg、jagged frontier、HITL 三時機（pre-act / mid-stream / post-hoc）、避免橡皮圖章化            |
| [4.6](/llm/04-applications/application-protocols/)                 | 應用層協議：function calling / structured output / MCP | 三者層級差異、為什麼出現 MCP、組合工作流                                                                      |
| [4.7](/llm/04-applications/workflow-patterns/)                     | Workflow 編排模式                                      | Pipeline / router / parallel / reflection 四種基本模式、退化條件                                              |
| [4.8](/llm/04-applications/multi-agent-topology/)                  | Multi-Agent 拓樸                                       | Flat / hierarchical / agent-as-tool、specialization gain vs orchestration overhead、特有失敗模式              |
| [4.9](/llm/04-applications/production-resource-planning/)          | Production 部署的資源評估原理                          | 6 個 dimension：concurrency / latency / cost / storage / observability / reliability                          |
| [4.10](/llm/04-applications/artifact-management/)                  | 衍生產物管理原理：什麼進 git、什麼不該                 | Source / derived / external 三分類、`.gitignore` 設計模式、prompt + eval 版本管理、production deployment 對接 |
| [4.11](/llm/04-applications/long-context-engineering/)             | Long context engineering                               | claimed vs effective context、lost-in-the-middle、跟 RAG 的取捨                                               |
| [4.12](/llm/04-applications/embedding-model-internals/)            | Embedding model 內部                                   | contrastive learning、選型、MTEB、in-domain fine-tune                                                         |
| [4.13](/llm/04-applications/eval-design-framework/)                | Eval 設計座標系：三軸、八象限                          | Objective / component / quantitative 三軸 × 工具選擇、軸誤選的訊號、eval 演化路徑                              |
| [4.14](/llm/04-applications/benchmarking-and-evaluation/)          | Benchmarking 與評估方法論                              | capability vs performance、in-house benchmark、`llama-bench`                                                  |
| [4.15](/llm/04-applications/vision-in-coding-workflow/)            | Vision in coding workflow                              | VLM 在 coding 場景的 use cases、本地 VLM 選型、IDE 整合現狀                                                   |
| [4.16](/llm/04-applications/static-and-serverless-rag-deployment/) | 靜態 / serverless RAG deployment                       | 沒 backend 的 RAG 四方案、API key 暴露、CORS、abuse、SaaS 供應鏈、跟模組六 routing                            |
| [4.17](/llm/04-applications/coding-agent-harness/)                 | Coding agent harness                                   | Scaffold vs harness 分層、context budget 25% 規則、subagent 設計、跟 Claude Code / Cursor / Aider 的 mapping  |
| [4.18](/llm/04-applications/prompt-caching-engineering/)           | Prompt caching 工程實務                                | Cache breakpoint 設計、coding agent / RAG 場景 pattern、anti-pattern、cost / latency 槓桿                     |
| [4.19](/llm/04-applications/agent-memory-architecture/)            | Agent memory 分層架構                                  | Working / session / episodic / semantic / procedural 四層、寫入時機、retrieval 設計、失敗模式                 |
| [4.20](/llm/04-applications/llm-tracing-and-observability/)        | LLM tracing 與 observability                           | OTel GenAI semconv、cost / latency / failure debug、trace → eval 閉環                                         |
| [4.21](/llm/04-applications/llm-as-judge/)                         | LLM-as-Judge 評估方法                                  | Rubric 設計、pairwise vs direct、三大 bias 緩解、calibration、跟 production trace 的閉環                      |
| [Hands-on](/llm/04-applications/hands-on/)                         | 端到端案例：把所有原理串成具體 case study              | Customer support agent 從 task decomposition 到 eval 全流程                                                   |

## 為什麼這個順序

本模組章節順序的設計脈絡：

1. **先 4.0 Prompt 技術光譜**：within-call 增強是後續所有設計的基底、先建立「prompt 層能做什麼、邊界在哪」的座標。
2. **接 4.1 RAG 原理 + 4.2 RAG 檢索增強**：應用層最常見的模式、把「LLM + 外部知識」這個基本組合走過一遍、概念對映到每個讀者都用過的 `@codebase` 等實務經驗。
3. **再 4.3 Tool use**：RAG 是「LLM 讀外部資料」、Tool use 是「LLM 對外部世界做事」、兩條延伸方向自然接續。
4. **再 4.4 Agent 架構 + 4.5 人機協作**：把 Tool use 從「單次呼叫」延伸到「自主多步」、自然進入 agent；agent 自主後立刻面對人類介入時機問題。
5. **再 4.6 應用層協議**：前面章節涉及 function calling、structured output、MCP 等術語、本章把這三個概念放回正確的層級、避免混為一談。
6. **再 4.7 Workflow + 4.8 Multi-agent**：上層整合、把多 LLM call 跟多 agent 組合的設計模式整理成跨 framework 不變的概念地圖。
7. **4.9 起進入 production / 細節**：部署資源、衍生產物管理、long context、embedding 內部、eval / benchmarking、tracing、judge——每個都是 production 場景遇到的具體議題。
8. **最後 hands-on**：把上述所有原理串成具體案例、看「實際做的時候、原理怎麼落」。

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
| 想做 LLM 應用開發                            | 重點讀 4.0、4.1–4.3、4.4–4.5、4.7–4.8、4.13   |
| 只想用本地 LLM 寫 code、不做應用             | 跳過本模組無妨、模組零 + 模組一已足夠        |

## 不在本模組內的主題

1. **具體 framework 教學**：LangChain、LlamaIndex 等的 API 用法、隨版本變、交給官方文件。
2. **具體 prompt 寫法**：跨模型跨任務不可遷移、本模組 4.0 寫的是 prompt 技術 landscape 的結構、不是具體寫法。
3. **具體 agent 工具配置**：aider、Cline 等的安裝設定、隨工具版本變、見 [1.6 延伸方向](/llm/01-local-llm-services/extension-paths/) 的入口資訊。
4. **訓練 / fine-tuning**：屬於改變模型本身、見 [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)。
