---
title: "OWASP LLM Top 10"
date: 2026-05-12
description: "LLM 應用最常見 10 大資安風險的業界共同詞彙、跟模組六本地 dev 視角的 mapping 表"
weight: 1
tags: ["llm", "knowledge-cards", "security", "owasp"]
---

OWASP LLM Top 10 的核心概念是「**Open Worldwide Application Security Project 發布的 LLM 應用最常見 10 大資安風險清單**」。2023 首發、2025 更新版是業界跟企業安全溝通的共同詞彙、是 production LLM 應用做 threat modeling 跟合規溝通的標準入口、涵蓋如 [prompt injection](/llm/knowledge-cards/prompt-injection/) 等風險類別。

## 跟其他概念的關係

2025 版的 10 項（簡述）：

| 編號  | 名稱                             | 簡述                                                                     |
| ----- | -------------------------------- | ------------------------------------------------------------------------ |
| LLM01 | Prompt Injection                 | 把惡意指令藏進 LLM 會讀到的內容、間接影響模型行為                        |
| LLM02 | Sensitive Information Disclosure | LLM 輸出洩漏訓練資料 / system prompt / PII                               |
| LLM03 | Supply Chain                     | 模型 / 訓練資料 / 工具 / dependency 供應鏈攻擊                           |
| LLM04 | Data and Model Poisoning         | 訓練資料污染、模型行為被植入後門                                         |
| LLM05 | Improper Output Handling         | LLM 輸出未驗證直接執行（XSS / SQLi / RCE）                               |
| LLM06 | Excessive Agency                 | Agent 工具權限過大、副作用不可控                                         |
| LLM07 | System Prompt Leakage            | System prompt 被使用者誘導露出                                           |
| LLM08 | Vector and Embedding Weaknesses  | Vector DB / embedding pipeline 的攻擊面                                  |
| LLM09 | Misinformation                   | [Hallucination](/llm/knowledge-cards/hallucination/) / 過度信任 LLM 輸出 |
| LLM10 | Unbounded Consumption            | Resource exhaustion / cost runaway（DoS / 燒錢）                         |

## 跟模組六的 mapping

| OWASP                       | 模組六章節                                                                                                                                                               | 補充                                                                                |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| LLM01 Prompt Injection      | [6.3 IDE 場景 prompt injection](/llm/06-security/prompt-injection-in-ide/)                                                                                               | 直接對應                                                                            |
| LLM02 Sensitive Disclosure  | [6.4 跨雲端資料邊界](/llm/06-security/cross-cloud-local-data-boundary/)                                                                                                  | 加 [4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) |
| LLM03 Supply Chain          | [6.0 模型供應鏈](/llm/06-security/model-supply-chain-trust/)                                                                                                             | 直接對應                                                                            |
| LLM04 Data/Model Poisoning  | 部分（限本地 dev、production 訓練屬 backend/07）                                                                                                                         | M6 cover 模型來源信任、不 cover 訓練毒化                                            |
| LLM05 Improper Output       | [6.2 tool use 權限](/llm/06-security/tool-use-permission-model/)                                                                                                         | 直接對應                                                                            |
| LLM06 Excessive Agency      | [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/) + [4.4 agent 架構](/llm/04-applications/agent-architecture/)                        | 跨原理 + 安全                                                                       |
| LLM07 System Prompt Leakage | 部分（[4.17 coding agent harness](/llm/04-applications/coding-agent-harness/)）                                                                                          | M6 沒專章、屬 scaffold 設計                                                         |
| LLM08 Vector / Embedding    | 部分（[4.1 RAG](/llm/04-applications/rag-principles/) + [4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/)）                               | 跨原理 + 應用                                                                       |
| LLM09 Misinformation        | [hallucination](/llm/knowledge-cards/hallucination/) 卡 + [4.21 LLM-as-judge](/llm/04-applications/llm-as-judge/)                                                        | 跨卡 + 應用                                                                         |
| LLM10 Unbounded Consumption | 部分（[4.18 prompt caching](/llm/04-applications/prompt-caching-engineering/) + [4.16 靜態 RAG 資安 abuse](/llm/04-applications/static-and-serverless-rag-deployment/)） | M6 沒專章、屬 abuse 緩解                                                            |

## 判斷條件與後果

安全團隊與 vendor security audit 都用 OWASP 的編號指稱風險。自己的應用對得上 LLM01 到 LLM10 時，跟對方溝通可以直接用編號指出哪一項風險、由哪個 control 處理；對不上時，雙方各自描述同一個風險，對話要先花在對齊用詞上。這份清單也涵蓋個人 dev 的情境：用 IDE agent 或本地模型時，LLM01 prompt injection、LLM03 supply chain、LLM06 excessive agency 一樣直接相關，因為 agent 會讀外部內容、下載的是第三方權重、手上有 tool 權限。本卡給定義與 mapping，個人 dev 場景對應的 control 在 [6.6 OWASP 對照章節](/llm/06-security/owasp-llm-top10-mapping/)。
