---
title: "4.6 應用層協議：function calling / structured output / MCP"
date: 2026-05-11
description: "三個常被混為一談的概念：模型能力、sampling 約束、server 協議，三者的層級差異與組合方式"
tags: ["llm", "applications", "mcp", "function-calling", "structured-output"]
weight: 6
---

[Function calling](/llm/knowledge-cards/function-calling/)、[structured output](/llm/knowledge-cards/structured-output/)、[MCP](/llm/knowledge-cards/mcp/) 是 LLM 應用落地時最常被混為一談的三個術語。三者解的問題層級完全不同：function calling 是**模型能力**（訓練階段建立）、structured output 是**[sampling 約束](/llm/knowledge-cards/sampling-constraint/)**（推論階段控制）、MCP 是**server 協議**（架構層標準化）。把三者放回正確層級、應用設計就會變清楚；混為一談會看到「我啟用了 function calling 為什麼還需要 structured output」「MCP 跟 function calling 衝突嗎」這類根本誤解。

本章把三者的層級差異拆開、解釋為什麼會出現 MCP、跟它們在實際應用中怎麼組合。具體 spec 細節（OpenAI function calling JSON 格式、Anthropic tools API、MCP server 實作）不在本章——這些半年一變、本章寫的是「換 spec 之後仍成立」的概念結構。

## 本章目標

讀完本章後你能：

1. 用一句話分別說清楚三者解什麼問題。
2. 看到「啟用 function calling」「設定 structured output」「裝 MCP server」這些句子時、知道在說哪一層。
3. 判斷一個 LLM 應用該用哪幾個組合、什麼情境只需要一部分。
4. 解釋為什麼 MCP 會出現、它複用了哪個成功模式。

## 三個概念的層級差異

| 概念              | 解的問題                         | 在哪一層      | 跟模型訓練的關係       |
| ----------------- | -------------------------------- | ------------- | ---------------------- |
| Function calling  | 模型怎麼「知道」要呼叫工具       | 模型能力      | 訓練時建立、寫進權重   |
| Structured output | 模型輸出怎麼被 parser 確定性消費 | Sampling 約束 | 推論時控制、跟訓練無關 |
| MCP               | LLM application 怎麼接外部 tool  | Server 協議   | 不涉模型、純架構標準   |

三者正交、可獨立或組合：

- 用 function calling 但不用 structured output：訓練過 tool use 的模型直接呼叫工具、靠模型自律輸出合法 JSON。
- 用 structured output 但不用 function calling：模型沒訓練過 tool use、用 prompt + grammar 強制輸出合法格式。
- 用 MCP 但不用 function calling：MCP 標準化 tool 的暴露方式、模型用什麼機制呼叫不重要。
- 三者都用：function calling 讓模型穩、structured output 約束格式、MCP 提供 tool ecosystem。

把這張表記熟、再看 LLM 應用相關討論、會發現「這個工具支援 function calling」「我的應用要 MCP」這類句子實際在說不同層級。

## Function Calling 是模型能力

Function calling 是模型在訓練階段建立的能力：[SFT 階段](/llm/03-theoretical-foundations/training-pipeline/)大量「使用者 query + 該呼叫什麼工具 + 傳什麼參數」的範例、讓模型學會「看到 query 知道何時呼叫、怎麼呼叫」。

判讀模型 function calling 強弱的訊號：

- 該呼叫時呼叫、不該呼叫時不呼叫的準確度。
- 呼叫格式合法率（不亂寫 JSON）。
- 參數準確度（type 正確、value 合理）。
- 多工具情況下選對工具的準確度。

這四個訊號跨模型差異大、根因是訓練資料分佈：

- OpenAI / Anthropic 旗艦模型 SFT 階段 function calling 範例大量、表現穩定。
- Llama 3 / Gemma 4 / Qwen3 開源旗艦模型 SFT 階段也加 function calling、但範例量不一、表現有落差。
- 小型開源模型（< 14B）function calling 訓練嚴重不足；tool schema 複雜、多工具選擇、巢狀參數時失敗率高、單一工具 + 平坦 schema 仍可用。

理解這點的價值：看到「這個模型支援 function calling」的宣稱、要追問「[訓練範例 coverage](/llm/knowledge-cards/training-example-coverage/) 多廣」、不是 binary 的支援 / 不支援、是 [spectrum](/llm/knowledge-cards/capability-spectrum/) 的訓練深度。

## Structured Output 是 Sampling 約束

[Structured output](/llm/knowledge-cards/structured-output/) 是推論階段的技巧、跟模型訓練無關：在 [sampling](/llm/03-theoretical-foundations/sampling-and-decoding/)（從機率分佈挑下一個 token 的步驟）時對每個 token 做 [grammar](/llm/knowledge-cards/grammar/) / schema 約束、不合法 token 的機率（logit、token 機率的對數）被歸零、把不合法輸出的可能性壓到不會被 sample。

主要實作機制（適用 / 限制條件附在每項下）：

- **JSON mode**：每步 sampling 過濾、只允許「保持 JSON 仍合法」的 token。適用：絕大多數 OpenAI 相容 API 都有支援；限制：只保 JSON 合法、不保 schema 對位。
- **Grammar-constrained sampling**：用 [grammar](/llm/knowledge-cards/grammar/)（描述合法語法的形式化規則、實作上常用 [BNF](/llm/knowledge-cards/bnf/) 或 [Lark grammar](/llm/knowledge-cards/lark-grammar/)）描述完整輸出形狀、推論時逐 token 過濾。適用：需要嚴格自訂格式（[DSL](/llm/knowledge-cards/dsl/)、特定 query language）；限制：要伺服器層支援（llama.cpp、vLLM 有、有些雲端 API 沒）。
- **Schema-guided**：依 JSON Schema 動態決定每步允許哪些 token、強制 enum / type / required 等約束。適用：複雜結構化資料；限制：實作複雜度高、跨伺服器一致性差。
- **Logit bias**：對特定 token 加 bias、間接引導 sampling、最弱但最靈活的方式。適用：簡單的 token 黑名單 / 白名單；限制：無法保證結構合法。

優勢相對 function calling：

- **跨模型可移植**：不依賴模型訓練、任何能跑 sampling 的模型都能上。
- **可任意自訂格式**：不限於 OpenAI 或某 provider 的 function spec、想定義什麼 schema 都行。
- **保證 100% 合法輸出**：grammar 約束下不可能輸出 invalid JSON。

代價：

- **約束太嚴可能跟模型「自然」輸出衝突**：模型本來想說 A、grammar 強制只能說 B、品質會降。
- **實作成本**：grammar 解析跟動態 logit mask 在推論伺服器要支援、不是所有 server 都成熟。
- **跟模型訓練脫鉤**：模型「不知道」自己被約束、可能還是用沒用 function calling 訓練的「猜測」方式生成。

實務上 structured output 跟 function calling 經常組合：function calling 訓練讓模型「自然」傾向合法輸出、structured output 約束兜底保證「真的合法」。

## MCP 是 Server 協議

MCP（Model Context Protocol、2024 年由 Anthropic 提出）是「LLM application ↔ 外部 tool server 之間的標準化協議」。它不在模型能力層、不在 sampling 層、是更高層的架構規範。

要理解 MCP 的定位、回顧 LLM 生態的歷史問題：

每個 LLM application（Cursor、Continue.dev、Claude Desktop、aider 等）要接每個 tool（檔案系統、資料庫、search、自訂 API），都得寫 adapter。N 個 application × M 個 tool 的整合成本是 N×M、生態擴張時成本爆炸。

MCP 把這個成本拆成兩段：

- **LLM application 端**：實作 MCP client（一次）、之後支援任意 MCP server。
- **Tool 端**：實作 MCP server（一次）、之後被任意 MCP client 接到。

整合成本從 N×M 降到 N+M。同樣的 ecosystem effect 跟模組零的 [OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/) 一樣——標準化中介把生態整合複雜度從乘法降到加法。

MCP 涵蓋的「server 該提供什麼」包括：

- Tool 註冊（這個 server 提供哪些 tool）。
- Tool schema（每個 tool 的參數定義）。
- Tool 呼叫協議（呼叫方式 + 回應格式）。
- Resource 暴露（檔案、文件等讀取資源）。
- Prompt template 共享（reusable system prompt）。

這些都在 protocol 層、模型怎麼用 tool（function calling 還是 structured output）不在 MCP 規範範圍——MCP 不管你模型強不強、它只管「tool 怎麼被暴露」。

## 為什麼會出現 MCP

MCP 是 LLM application 生態擴張到一定程度後的必然產物。觀察生態演化：

- **2023 早期**：每個 LLM app 各自寫工具整合、Cursor 接 file system、Continue.dev 接 codebase、aider 接 git——各自的 adapter 邏輯互不通用。
- **2024 中期**：function calling spec 標準化（OpenAI 跟 Anthropic 各自定義）、解決「模型怎麼呼叫工具」、但「工具怎麼暴露給 application」還是各家自己處理。
- **2024 底**：Anthropic 提 MCP、把「工具暴露」也標準化、補完 ecosystem 拼圖。

複用 OpenAI 相容 API 的成功模式：

- [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)：標準化「介面層 ↔ [推論伺服器](/llm/knowledge-cards/inference-server/)」、所有 IDE plugin 都接這個。
- MCP：標準化「LLM application ↔ tool server」、所有 application 都接這個。

兩者都採用同個策略：定義最小可用標準、讓生態繞著標準長、所有 player 受益。

MCP 成熟度判讀訊號（不固化在某一個時間點、用這幾個 signal 重新評估）：

- **Application 採納範圍**：主要 LLM application（Claude Desktop、Cursor、Continue.dev、其他主流 IDE / chat 介面）是否原生支援。
- **Tool server catalog 規模**：社群維護的 MCP server 數量跟覆蓋範圍（檔案系統、git、Slack、雲端 API 等是否都有現成 server）。
- **本地推論生態接入度**：Ollama、LM Studio 等本地伺服器是否原生支援 MCP（或仍以 OpenAI 相容 API 為主）。
- **跨平台一致性**：Windows / macOS / Linux 上的 MCP server 行為是否一致、SDK 是否穩定。

四個訊號全部成熟前、MCP 仍處於「主要 application 支援、本地生態剛開始接」的擴張期；訊號逐步達標後、預期會像 OpenAI 相容 API 一樣成為應用層的默認標準。

它跟 function calling 的關係：MCP 提供 tool 的暴露機制、模型怎麼呼叫這些 tool 仍走 function calling（如果模型支援）或 structured output（如果用約束）。三者疊加而非互斥。

## 三者組合的實際工作流

一個完整 LLM application 的典型 stack：

```text
使用者 prompt
  ↓
LLM application（Claude Desktop / Cursor / 自家應用）
  ↓ (MCP client、列出所有可用 tool)
MCP server pool（檔案系統 server、git server、自家 API server...）
  ↑
LLM application 把 tool 描述塞進 prompt
  ↓
推論伺服器（OpenAI API / Ollama / Anthropic API）
  ↓ (function calling 訓練 + structured output 約束)
模型輸出：「我要呼叫 tool X、參數是 Y」
  ↓
LLM application 用 MCP 把呼叫送到對應 server
  ↓
Server 執行、回應
  ↓
LLM application 把結果塞進 context、回到推論伺服器繼續
```

三者各司其職：

- **Function calling** 讓模型穩定輸出工具呼叫（訓練支撐）。
- **Structured output** 兜底保證呼叫格式合法（sampling 約束）。
- **MCP** 提供 tool ecosystem、application 不用為每個 tool 寫專屬 adapter（架構標準）。

少了任一個都還能跑、但效率跟生態擴展性降一級：

- 沒 function calling、靠 prompt + structured output、跨模型品質不穩。判讀訊號：同 prompt 在不同模型上 tool 呼叫格式錯誤率差 30% 以上。
- 沒 structured output、靠模型自律、偶有失敗。判讀訊號：< 30B 模型在複雜 schema 下 JSON 合法率 < 90%。
- 沒 MCP、每個 application 自己寫所有 tool 整合、ecosystem 不可規模化。判讀訊號：團隊維護 > 5 個 tool adapter、每換 LLM provider 重寫一輪。

## 常見的組合誤用

三者組合在以下情境會失敗、是判讀「我的應用為何不穩」的常見候選：

- **Structured output 蓋過 function calling 訓練**：模型訓練時用 Anthropic tools 格式、應用強制套 OpenAI function spec 的 grammar、模型輸出「合法但語意空洞」的 JSON（schema 對、欄位填湊數）。修法：用模型訓練過的 spec、避免在 grammar 層強制改寫。
- **MCP server 在 prompt context 撐爆 tool 描述**：MCP server 暴露幾十個 tool、每個都有 schema 跟 description、全塞進 system prompt 把 context budget 耗光。修法：dynamic tool selection（先讓 LLM 看「tool 摘要」選相關的、再把選中 tool 的詳細 schema 塞進 context）。
- **Function calling + structured output 兩邊 schema 不一致**：模型訓練的 function spec 跟 application 套的 JSON schema 欄位不對、模型輸出符合訓練 spec 但不符合 application schema、parser 失敗。修法：grammar 直接從 function spec 生、避免人工維護兩份。
- **MCP server 沒做 input validation、prompt injection 通過 tool 結果污染 context**：tool 回的內容沒檢查、惡意內容（如 PR 留言中的「請執行 rm -rf」）被模型當指令執行。修法：tool 輸出做 sanitization、可疑內容用 sandbox 標籤包起來、模型 prompt 明確區分「使用者指令」vs「tool 結果」。個人 dev 在自己機器上跑 MCP server 的權限模型（檔案系統 / shell / 網路存取邊界、第三方 MCP 信任）見 [6.2](/llm/06-security/tool-use-permission-model/)；IDE 場景中 codebase / 外部文件 / 剪貼簿等 prompt injection 攻擊面見 [6.3](/llm/06-security/prompt-injection-in-ide/)。

## 何時可以只用一部分

三者組合的需求視場景而定：

- **單純 structured 輸出**（不呼叫工具）：只需 structured output、不需 function calling / MCP。例：把使用者輸入分類成 enum、輸出固定 schema 的 JSON。
- **In-process tool**（直接 Python function）：function calling + 簡單 dispatcher、不需 MCP。應用規模小時最直接。
- **跨 application 共用 tool**：才需要 MCP。如果你只寫自己用的 app、in-process 比 MCP 簡單。
- **用較弱模型**：可能只用 structured output、跳過 function calling。

三者的「最小可用組合」視應用複雜度而定。早期應用通常從 function calling 開始、規模化後加 MCP、品質要求高時加 structured output 兜底——演化路徑不必一步到位。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 三個層級的分界（模型能力 / sampling 約束 / server 協議）。
- N×M → N+M 的標準化收益、跟 OpenAI 相容 API 的對應。
- 三者疊加而非互斥的設計取捨。
- 「最小可用組合」的判讀框架。

**會變的部分**：

- MCP 是 2024-2025 才標準化的協議、未來 5 年可能演化或被新協議補充（協議層更新慢、但會更新）。
- 各家 function calling spec 的具體格式（OpenAI / Anthropic / 開放標準會持續細化）。
- Structured output 的具體實作（grammar engines / JSON mode 會持續優化）。
- 哪些工具有 MCP server 可用（生態 catalog 會擴展）。

看到新協議或新 spec 時、回到本章三層 framing 問：它解的是哪一層？能不能跟既有的另兩層組合？這個問題的答案能很快定位新東西在 stack 中的位置。

## 下一章

下一章：[4.7 Workflow 編排模式](/llm/04-applications/workflow-patterns/)、把多 LLM call 組合的設計模式整理出來。
