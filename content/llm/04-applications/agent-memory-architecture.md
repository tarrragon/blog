---
title: "4.19 Agent memory 分層架構"
date: 2026-05-12
description: "Agent 在 context window 之外管理長期狀態的設計：working / short-term / long-term episodic / semantic / procedural 五個層次、寫入時機、retrieval 設計、失敗模式"
tags: ["llm", "applications", "agent", "memory", "rag"]
weight: 19
---

LLM 本身無狀態 — 每次 [forward pass](/llm/knowledge-cards/forward-pass/) 從零開始、唯一輸入是 [context window](/llm/knowledge-cards/context-window/)。但「agent」概念上有跨 session 狀態：使用者偏好、過去任務、累積知識、操作流程。Agent memory 是 harness 層的設計、把這些狀態持久化、按需 inject 到 working context。本章把 memory 分成五個層次、各層的寫入時機、retrieval 設計、失敗模式拆成可操作的工程實務。

## 本章目標

讀完本章後、你應該能：

1. 區分 [agent memory](/llm/knowledge-cards/agent-memory/) 的五個層次（working / short-term / long-term episodic / semantic / procedural）。
2. 對自己 agent 場景判斷要哪幾層 memory、不要哪幾層。
3. 設計 long-term memory 的「何時寫」「何時讀」邏輯。
4. 認識 memory 的常見失敗模式（drift / PII / 污染）跟對應緩解。

## 五個層次的責任劃分

```text
[Working memory]：當前 forward pass 的 context window
   - 規模：模型 context（4K-1M token）
   - 範圍：當下這次推論的全部輸入
   - 例：當下 user query + recent tool result + reasoning trace

       ↑ 從這層讀 / 寫到這層

[Short-term / session memory]：單一 session 的 scratchpad
   - 規模：一輪對話到一天
   - 範圍：跨多個 turn、但 session 結束就丟
   - 例：本 session 算過的中間結果、tried strategies

       ↑ session 結束時可選擇 persist 到 long-term

[Long-term episodic memory]：跨 session 的「事件」
   - 規模：永久（直到主動刪除）
   - 範圍：跨所有 session、按時間順序
   - 例：「上週解過這個 race condition」「alice 上個月問過 X」

[Long-term semantic memory]：跨 session 的「事實 / 知識」
   - 規模：永久
   - 範圍：跨所有 session、按主題索引
   - 例：「user 偏好 markdown 輸出」「專案用 React 18」「team 不用 Tailwind」

[Long-term procedural memory]：跨 session 的「流程 / 技能」
   - 規模：永久
   - 範圍：可重複使用的 known-good 程序
   - 例：「跑測試前先 npm install」「commit 前要 lint」「deploy 前要 dry-run」
```

跟人類認知科學的對應：working ≈ 短期工作記憶、episodic ≈ 「我昨天去哪裡了」、semantic ≈ 「巴黎是法國首都」、procedural ≈ 「騎腳踏車的肌肉記憶」。

## 不是每個 agent 都要五個層次都用

選擇看用例：

| 用例                                 | Working | Session | Episodic | Semantic | Procedural |
| ------------------------------------ | ------- | ------- | -------- | -------- | ---------- |
| Autocomplete（單行補完）             | ✅      | ❌      | ❌       | ❌       | ❌         |
| Single-turn Q&A                      | ✅      | ❌      | ❌       | ❌       | ❌         |
| Chat IDE assistant（短對話）         | ✅      | ✅      | ❌       | ❌       | ❌         |
| Chat IDE assistant（長期使用）       | ✅      | ✅      | 可選     | ✅       | 可選       |
| 長期 coding agent（持續同 codebase） | ✅      | ✅      | ✅       | ✅       | ✅         |
| Multi-session research agent         | ✅      | ✅      | ✅       | ✅       | ✅         |

實務啟示：從「最少 memory」開始、有具體 trigger 才加。memory 不是越多越好、每加一層都增加複雜度跟失敗面。

## Long-term memory 的寫入時機

**何時寫**是設計核心、影響 memory 的品質跟成本。三種主流模式：

### 1. 每 turn 寫（Auto-write）

每個對話 turn 結束都寫一條 memory。實作簡單但 memory 變垃圾場 — 太多瑣碎內容、retrieval 時混淆 signal。

**適合**：實驗階段、想看 memory 怎麼累積
**不適合**：production、長期使用

### 2. 任務結束寫（Task-end write）

每個明確「任務」（如「修完 bug」「寫完 feature」）結束時、寫一條 episodic / semantic memory 摘要。

實作：

```text
任務開始 → working memory 進入「task mode」
   ↓ 多 turn 累積 session scratchpad
任務結束（user 說「好了」/ test 通過 / commit done）
   ↓ trigger memory write
LLM call：「請從本 session 提取值得記得的 episodic / semantic / procedural memory」
   ↓ 結構化輸出
寫進 long-term store
```

**適合**：production agent、明確任務邊界
**不適合**：開放式對話、無明確任務終點

### 3. 主動觸發寫（Reflection / consolidation）

定期（每 N turn / 每天）跑「memory consolidation」step、LLM 自己決定該寫什麼。借鑒人類睡眠時 memory consolidation 的研究。

**適合**：長 running agent、有明確 idle 時間
**不適合**：低 cost 場景（consolidation 額外 LLM call 是常駐成本）

混用：production 多用「task-end write」為主 + 偶爾 reflection 做 consolidation。

## Long-term memory 的 retrieval

**何時讀**也是設計核心。三種主流模式：

### 1. Inject-on-startup

把 long-term memory 在 session / agent 啟動時一次塞進 system prompt。

```text
System prompt:
  "你是 coding assistant、user alice。
   semantic memory: {markdown 偏好、React 18、Python 3.11、...}
   procedural memory: {npm install before test、lint before commit、...}"
```

**適合**：memory 量小（< 1K token）、相對穩定
**不適合**：memory 多、變動快、retrieval 不準

### 2. Retrieval-on-demand

每次 user query 來、用 [embedding similarity](/llm/04-applications/embedding-model-internals/) 從 vector store retrieve 相關 memory、塞進 context。

```text
User query → embed → cosine similarity vs memory vectors → top-K → inject
```

**適合**：memory 量大、跨主題、需要動態
**不適合**：高頻 / 低 latency 要求（retrieval overhead）

### 3. Hybrid（混合）

Procedural / semantic（穩定）→ inject-on-startup；episodic（動態）→ retrieval-on-demand。

```text
Session 啟動：
  inject procedural + semantic（小、穩定）

每 user query：
  retrieve top-K episodic（動態）+ inject
```

實務 production 多採 hybrid。

## 跟 [RAG](/llm/knowledge-cards/rag/) 的邊界

Agent memory 跟 RAG 容易混淆、實際上是不同概念：

| 維度           | RAG                                | Long-term agent memory          |
| -------------- | ---------------------------------- | ------------------------------- |
| 主要內容       | 外部知識庫（docs、wiki、codebase） | Agent 跟特定 user 的互動歷史    |
| Per-user？     | 通常通用                           | Per-user / per-session          |
| 寫入時機       | Build time / ingestion pipeline    | Runtime（agent 自己決定何時寫） |
| 變動頻率       | 較慢（doc 更新）                   | 快（每 session 都可能變）       |
| 是否含「事件」 | 否（純知識）                       | Episodic memory 是事件          |

但兩者實作層常共享：vector store / embedding model / retrieval logic 可重用。設計上：

- **如果讀者問「跟『過去聊過的事』有關」→ memory**
- **如果讀者問「跟『某個固定知識』有關」→ RAG**
- **同一個 query 兩者都要 → hybrid retrieval、結果合併**

## 失敗模式

### 1. Memory drift（記憶過時）

舊 memory 寫的內容不再正確、但仍被 retrieve、agent 用過時資訊。

**例**：兩個月前寫 memory「user 偏好 React class component」、user 已換 hooks、agent 仍寫 class component。

**緩解**：

- Memory 加 timestamp、retrieval 時加 time decay weighting
- 定期 consolidation：LLM 跑一遍判斷哪些 memory 過時
- Procedural / semantic memory 跑「validation step」：當前對話是否仍 align、不 align 就 mark stale

### 2. PII 寫入

User 不知情下、agent 把 PII（email、phone、社群 ID）寫進 long-term memory、跨 session retrieve 出來、可能洩漏。

**緩解**：

- Memory write 前過 PII detection（regex 或專門模型）
- Memory store 加 encryption-at-rest
- User 可看 / 編輯 / 刪除自己 memory（GDPR / 隱私法規要求）
- 跟 [6.4 跨雲端資料邊界](/llm/06-security/cross-cloud-local-data-boundary/) 結合判讀

### 3. Context 污染

不相關 memory 被 retrieve 進 working memory、模型把 irrelevant 內容當 signal、輸出飄。

**例**：user 問 React 問題、retrieve 出兩個月前的 Vue 經驗、模型混淆。

**緩解**：

- Retrieval 加 similarity threshold（< 0.7 不 inject）
- Memory 加 metadata（topic / project / language）、retrieval 加 filter
- Inject 後加 explicit framing：「以下是過去相關 memory、僅供參考、若跟當前問題不符請忽略」

### 4. Memory 跟 hallucination 互相 boost

[Hallucination](/llm/knowledge-cards/hallucination/) 寫進 memory、變成「事實」、後續 retrieve 強化 hallucination、agent 越來越相信錯誤內容。

**緩解**：

- Memory write 前要求 LLM 標「不確定」flag、retrieval 時 deprioritize
- 定期 ground truth validation（如連結 memory 到實際檔案、檔案變了 memory 失效）
- Critical memory 要 user 確認才寫入

### 5. 跨 user memory 污染

Production 多 user 場景、memory store 沒做 user isolation、A user 的 memory 流到 B user。

**緩解**：

- Memory store schema 強制 user_id 索引
- Retrieval query 必加 user_id filter
- 跟 [6.5 routing-to-production](/llm/06-security/routing-to-production-security/) 的多租戶 isolation 結合

## 主流實作

| 工具 / framework        | 特色                                             |
| ----------------------- | ------------------------------------------------ |
| Mem0                    | 開源、五層 memory framework、retrieval-on-demand |
| Letta（前 MemGPT）      | LLM-managed memory hierarchy、自動 page in/out   |
| LangGraph memory        | LangChain 系、跟 graph workflow 整合             |
| Zep                     | 雲端 memory service、含 PII detection            |
| Self-implemented（DIY） | 多數 production 自寫、用 vector store + metadata |

判讀：用既有 framework vs 自己寫、取決於 memory 邏輯複雜度。簡單 case（per-user semantic preferences）用 DIY 即可；多層 memory + consolidation + GDPR 合規要 framework / SaaS。

## 跟 Coding agent 的整合

Coding agent 場景的 memory 案例：

| Memory 類型 | 內容例子                                                                  |
| ----------- | ------------------------------------------------------------------------- |
| Semantic    | 「專案用 TypeScript strict mode」「team 不用 anonymous default export」   |
| Procedural  | 「跑測試 = `npm test`」「commit 前 `npm run lint`」                       |
| Episodic    | 「上週解過 race condition 在 user_session.ts」「alice 的 retry 邏輯偏好」 |

跟 [4.17 coding agent harness](/llm/04-applications/coding-agent-harness/) 的關係：

- Procedural memory 編進 [scaffold](/llm/knowledge-cards/scaffold-vs-harness/) 的 system prompt 或 skill registry
- Semantic memory 可 inject-on-startup 或 retrieval-on-demand
- Episodic memory 用 retrieval-on-demand、跟 [RAG](/llm/04-applications/rag-principles/) 共享 infrastructure

## 何時過時 / 何時不過時

**不會過時的部分**：

- 五層 memory 分類（working / session / episodic / semantic / procedural）
- 「不是每個 agent 都要五層都用」的選擇框架
- 寫入時機的三種模式（auto / task-end / reflection）
- Retrieval 的三種模式（inject / retrieval / hybrid）
- 五個失敗模式分類

**會變的部分**：

- 具體 framework（Mem0 / Letta / LangGraph）的 API
- LLM-managed memory 的具體實作（如 MemGPT 風格的 paging）
- Memory consolidation 的最佳實踐
- 整合 LLM 跟 vector store / DB 的最佳方式

## 下一章

下一章：[4.20 LLM tracing 與 observability](/llm/04-applications/llm-tracing-and-observability/)、看 production debug 跟 cost 監控的工具層。
