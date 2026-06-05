---
title: "6.6 OWASP LLM Top 10 對照圖"
date: 2026-05-12
description: "把模組六的本地 dev 視角安全章節對照到 OWASP LLM Top 10 2025、補出個人 dev 場景跟企業合規溝通的共同詞彙"
tags: ["llm", "security", "owasp", "compliance"]
weight: 7
---

模組六前面六章是「個人 dev 視角」的本地 LLM 安全議題、用本 blog 自己的 framing 組織。但企業 / 合規 / vendor audit 場景的共同詞彙是 [OWASP LLM Top 10](/llm/knowledge-cards/owasp-llm-top10/)（2023 首發、2025 更新版）。本章把模組六 + 模組四相關章節對照到 OWASP 編號、補出「同議題、不同詞彙」的 mapping、讓讀者跟企業安全 team 溝通時能 align。

## 本章目標

讀完本章後、你應該能：

1. 對照 OWASP LLM Top 10（LLM01-LLM10）跟自己工作流的具體風險。
2. 看到 enterprise security audit 報告用 OWASP 編號、能 map 到模組六章節找對應 control。
3. 知道哪些 OWASP 項目模組六完整覆蓋、哪些只覆蓋部分、哪些屬其他模組或 backend/07。

## OWASP LLM Top 10 2025

OWASP（Open Worldwide Application Security Project）的 LLM 應用安全清單、2025 更新版：

| 編號  | 名稱                             | 一句話描述                                        |
| ----- | -------------------------------- | ------------------------------------------------- |
| LLM01 | Prompt Injection                 | 惡意指令藏進 LLM 會讀到的內容、間接影響模型行為   |
| LLM02 | Sensitive Information Disclosure | LLM 輸出洩漏訓練資料 / system prompt / PII / 機密 |
| LLM03 | Supply Chain                     | 模型 / 訓練資料 / 工具 / dependency 供應鏈攻擊    |
| LLM04 | Data and Model Poisoning         | 訓練資料污染、模型行為被植入後門                  |
| LLM05 | Improper Output Handling         | LLM 輸出未驗證直接執行（XSS / SQLi / RCE）        |
| LLM06 | Excessive Agency                 | Agent 工具權限過大、副作用不可控                  |
| LLM07 | System Prompt Leakage            | System prompt 被使用者誘導露出                    |
| LLM08 | Vector and Embedding Weaknesses  | Vector DB / embedding pipeline 的攻擊面           |
| LLM09 | Misinformation                   | Hallucination / 過度信任 LLM 輸出                 |
| LLM10 | Unbounded Consumption            | Resource exhaustion / cost runaway（DoS / 燒錢）  |

> **事實查核註**：OWASP 列表會定期更新（2023 → 2025、未來會有新版）、引用前以 [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) 當前版為準。

## 詳細 mapping

### LLM01 Prompt Injection

**OWASP 範圍**：使用者輸入 / 外部資料 / RAG retrieved content 中藏指令、影響模型行為。包含 direct injection（user 自己注）跟 indirect injection（內容裡有人塞）。

**模組六對應**：

- **主章節**：[6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)
- **覆蓋**：間接注入（codebase / 第三方依賴 / issue / 剪貼簿 / web fetch）、本地 LLM 跟雲端 LLM 的抵抗能力差異、IDE 場景的具體入口
- **不在 M6 範圍**：production agent 場景的 prompt injection 後果（資料外洩 / 誤觸 tool）見 [backend/07 LLM agent prompt injection](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)

**個人 dev 場景的最低 control**：RAG exclude `.env` / secrets、tool use 加 confirm（見 [6.2](/llm/06-security/tool-use-permission-model/)）、agent loop 設 max steps、untrusted 來源內容明確標記

### LLM02 Sensitive Information Disclosure

**OWASP 範圍**：模型輸出洩漏訓練資料、system prompt、PII、商業機密、API key。

**模組六對應**：

- **主章節**：[6.4 跨雲端 / 本地的資料邊界](/llm/06-security/cross-cloud-local-data-boundary/)
- **覆蓋**：跨雲端 prompt 邊界、第三方 plugin 偷送 prompt、API key 不放在前端 JS
- **補充章節**：[4.16 靜態 / serverless RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) 的 API key 暴露段、user query 隱私段
- **不在 M6 範圍**：企業合規（GDPR / HIPAA / SOC 2）的逐條檢核屬 [backend/07](/backend/07-security-data-protection/)

**個人 dev 場景的最低 control**：本地敏感任務不送雲端、雲端 model 明確標記、API key 從環境變數讀

### LLM03 Supply Chain

**OWASP 範圍**：模型權重、訓練資料、tokenizer、dependency 套件、MCP server 等的供應鏈風險。

**模組六對應**：

- **主章節**：[6.0 模型供應鏈與信任邊界](/llm/06-security/model-supply-chain-trust/)
- **覆蓋**：GGUF / HuggingFace / Ollama registry 信任、量化版本污染、權重完整性、MCP server 信任
- **補充**：[4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) 的 client-side LLM 模型 CDN 信任段
- **不在 M6 範圍**：production 模型 release / SBOM / artifact provenance 屬 [backend/07 supply chain](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)

**個人 dev 場景的最低 control**：選主流作者 / 量化者、下載後 hash 比對、MCP server 跑 sandbox

### LLM04 Data and Model Poisoning

**OWASP 範圍**：訓練資料被植入惡意樣本、fine-tune 資料污染、模型行為後門。

**模組六對應**：**部分覆蓋**

- **覆蓋**：[6.0 模型供應鏈](/llm/06-security/model-supply-chain-trust/) 的「量化版本污染」段、選主流作者的 framing
- **不在 M6 範圍**：自己 train base model 或 large-scale fine-tune 的資料治理屬研究 / production team 範圍、見 [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/) 概念 + [1.x hands-on local-fine-tune](/llm/01-local-llm-services/hands-on/local-fine-tuning/) 的小規模 fine-tune 注意事項

**個人 dev 場景的最低 control**：個人 dev 多用既有模型、threat model 不涵蓋自訓 base、用主流作者降低 poisoning 風險

### LLM05 Improper Output Handling

**OWASP 範圍**：把 LLM 輸出直接餵給下游系統（執行、render、SQL query）、若 LLM 輸出含惡意內容、下游 XSS / SQLi / RCE。

**模組六對應**：

- **主章節**：[6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)
- **覆蓋**：tool 副作用範圍 spectrum、可逆性、confirm 機制
- **補充原理**：[4.3 tool use 副作用範圍設計](/llm/04-applications/tool-use-principles/)
- **不在 M6 範圍**：web app 場景的 output sanitization、CSP、render escape 屬一般 web 安全 + [backend/07](/backend/07-security-data-protection/)

**個人 dev 場景的最低 control**：副作用類 tool 加 confirm、shell 命令前 review、git track + diff

### LLM06 Excessive Agency

**OWASP 範圍**：Agent 工具權限過大、副作用範圍超出需求、agent loop 太自主沒人類審查。

**模組六對應**：

- **主章節**：[6.2 tool use 權限](/llm/06-security/tool-use-permission-model/) + [4.4 Agent 跟人類審查協作](/llm/04-applications/agent-architecture/)
- **覆蓋**：sandbox / 白名單 / 副作用可逆性、agent 人類審查 spectrum、coding agent 的 permission boundary（[hands-on](/llm/01-local-llm-services/hands-on/permission-boundary/)）
- **補充**：[4.17 coding agent harness](/llm/04-applications/coding-agent-harness/) 的 permission boundary 設計

**個人 dev 場景的最低 control**：副作用 tool 加 confirm、agent max steps、production-level tool 不放在 dev agent 可達範圍

### LLM07 System Prompt Leakage

**OWASP 範圍**：使用者透過 prompt engineering 誘導 LLM 露出 system prompt 內容、暴露商業邏輯 / 提示工程 know-how。

**模組六對應**：**部分**

- **覆蓋**：[4.17 coding agent harness](/llm/04-applications/coding-agent-harness/) 的 scaffold 設計提到 system prompt 是核心元件、但沒專門講 leakage
- **不在 M6 範圍**：sysprompt leak 主要是 production 商業祕密議題、屬 backend/07 / 各 vendor docs

**個人 dev 場景的最低 control**：不要把 secret（API key、internal info）寫在 system prompt、敏感邏輯放後端而非 prompt

### LLM08 Vector and Embedding Weaknesses

**OWASP 範圍**：Vector DB 被污染、embedding model 被攻擊、retrieval pipeline 被注入毒文件、跨租戶 vector 污染。

**模組六對應**：**部分**

- **覆蓋**：[4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) 的「第三方 SaaS 信任」段、跨租戶 isolation 議題
- **補充原理**：[4.1 RAG 原理](/llm/04-applications/rag-principles/) 的失敗模式、[4.12 embedding model 內部](/llm/04-applications/embedding-model-internals/)
- **不在 M6 範圍**：production multi-tenant vector DB 屬 [backend/07 多租戶 isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)

**個人 dev 場景的最低 control**：RAG ingestion 加 PII / secret filter、vector DB 選 search-only key、不混跨 user vector

### LLM09 Misinformation

**OWASP 範圍**：LLM hallucination 被當真實、使用者過度信任輸出做 critical 決定。

**模組六對應**：**跨章節**

- **概念基礎**：[hallucination 卡](/llm/knowledge-cards/hallucination/)
- **評估方法**：[4.14 benchmarking](/llm/04-applications/benchmarking-and-evaluation/) + [4.21 LLM-as-judge](/llm/04-applications/llm-as-judge/)
- **應用層緩解**：[4.1 RAG](/llm/04-applications/rag-principles/)（給 LLM 外掛真實知識）、[4.4 agent](/llm/04-applications/agent-architecture/) 的人類審查 spectrum
- **不在 M6 範圍**：M6 預設 dev 自己驗證輸出、不專章寫

**個人 dev 場景的最低 control**：critical 任務人類 review、複雜推理用 reasoning model、code 生成必跑 test

### LLM10 Unbounded Consumption

**OWASP 範圍**：Resource exhaustion（context / token / GPU memory 燒爆）、cost runaway（API quota 被偷用 / agent 無限 loop 燒錢）。

**模組六對應**：**部分**

- **覆蓋**：[4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) 的「rate limit / abuse」段、靜態前端被 scrape 後燒 LLM quota 的情境
- **補充**：[4.18 prompt caching](/llm/04-applications/prompt-caching-engineering/)（[Prompt Cache](/llm/knowledge-cards/prompt-cache/)、cost 控制）、[4.4 agent](/llm/04-applications/agent-architecture/) 的 termination（max steps / cost cap）、[4.17 coding agent harness](/llm/04-applications/coding-agent-harness/) 的 budget management
- **不在 M6 範圍**：production rate limiting / DDoS 防護屬 [backend/07 entrypoint protection](/backend/07-security-data-protection/entrypoint-and-server-protection/)

**個人 dev 場景的最低 control**：agent 設 max_steps / max_cost、API key 不放前端 JS、用 edge function 加 rate limit

## 速查表

按 OWASP 編號排序、給定 OWASP 項目可快速找對應 control 章節：

| OWASP | 主章節                                                                                                                                         | 補充章節 / 卡片                                                                                                                                                   |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM01 | [6.3](/llm/06-security/prompt-injection-in-ide/)                                                                                               | [4.4 agent loop](/llm/04-applications/agent-architecture/)、[hands-on permission-boundary](/llm/01-local-llm-services/hands-on/permission-boundary/)              |
| LLM02 | [6.4](/llm/06-security/cross-cloud-local-data-boundary/)                                                                                       | [4.16 靜態 RAG](/llm/04-applications/static-and-serverless-rag-deployment/)、[0.7](/llm/00-foundations/privacy-data-flow/)                                        |
| LLM03 | [6.0](/llm/06-security/model-supply-chain-trust/)                                                                                              | [4.16 client-side LLM 段](/llm/04-applications/static-and-serverless-rag-deployment/)                                                                             |
| LLM04 | [6.0](/llm/06-security/model-supply-chain-trust/) 部分                                                                                         | [3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)、[hands-on fine-tune](/llm/01-local-llm-services/hands-on/local-fine-tuning/)                  |
| LLM05 | [6.2](/llm/06-security/tool-use-permission-model/)                                                                                             | [4.3 tool use 原理](/llm/04-applications/tool-use-principles/)                                                                                                    |
| LLM06 | [6.2](/llm/06-security/tool-use-permission-model/) + [4.4](/llm/04-applications/agent-architecture/)                                           | [4.17 coding agent harness](/llm/04-applications/coding-agent-harness/)、[hands-on permission-boundary](/llm/01-local-llm-services/hands-on/permission-boundary/) |
| LLM07 | [4.17 scaffold](/llm/04-applications/coding-agent-harness/) 部分                                                                               | [system prompt 卡](/llm/knowledge-cards/system-prompt/)                                                                                                           |
| LLM08 | [4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) 部分                                                          | [4.1 RAG](/llm/04-applications/rag-principles/)、[4.12 embedding](/llm/04-applications/embedding-model-internals/)                                                |
| LLM09 | [hallucination 卡](/llm/knowledge-cards/hallucination/) + [4.21](/llm/04-applications/llm-as-judge/)                                           | [4.1 RAG](/llm/04-applications/rag-principles/)、[4.14 benchmarking](/llm/04-applications/benchmarking-and-evaluation/)                                           |
| LLM10 | [4.16 abuse 段](/llm/04-applications/static-and-serverless-rag-deployment/) + [4.18 caching](/llm/04-applications/prompt-caching-engineering/) | [4.4 termination](/llm/04-applications/agent-architecture/)、[4.17 budget](/llm/04-applications/coding-agent-harness/)                                            |

## 跟 backend/07 的分工再述

模組六是「**個人 dev 視角**」、跟 [backend 模組七 資安](/backend/07-security-data-protection/) 是分工關係（[6.5 routing-to-production-security](/llm/06-security/routing-to-production-security/) 有詳細）：

| 場景                             | 看哪                                                                                               |
| -------------------------------- | -------------------------------------------------------------------------------------------------- |
| 個人 dev 在自己機器跑、純粹本地  | 模組六 + 模組四                                                                                    |
| 個人 dev 用雲端 API、自己機器跑  | 模組六 + 模組四 + [4.16 靜態 RAG 資安](/llm/04-applications/static-and-serverless-rag-deployment/) |
| 團隊內部部署 LLM、給內部用戶用   | 模組六 + [backend/07 部分](/backend/07-security-data-protection/)                                  |
| Production multi-tenant LLM 服務 | [backend/07 全部](/backend/07-security-data-protection/)（多租戶 isolation、合規、incident）       |

OWASP LLM Top 10 是兩邊共用詞彙、不限本地或 production。

## 何時過時 / 何時不過時

**不會過時的部分**：

- OWASP LLM Top 10 作為企業合規溝通共同詞彙的地位
- 本章 mapping 表的 framing（每個 OWASP 項對應模組六哪章 / 部分覆蓋 / 跨模組）
- 模組六跟 backend/07 的分工

**會變的部分**：

- OWASP 清單本身（2023 → 2025 → 未來新版、項目可能調整）
- 具體 vendor security audit 的範本（不同 vendor / industry 不同）
- 跟其他 framework（NIST AI RMF、ISO/IEC 42001）的對照

## 下一步

本章是模組六最後一章。production 多租戶服務化資安見 [backend 模組七](/backend/07-security-data-protection/)。
