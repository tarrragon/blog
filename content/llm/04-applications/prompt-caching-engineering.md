---
title: "4.13 Prompt caching 工程實務：cost / latency 最大槓桿"
date: 2026-05-12
description: "Prompt cache 怎麼運作、cache_control 設計、coding agent 跟 long-context 的 cache pattern、anti-pattern 跟 cache miss 訊號"
tags: ["llm", "applications", "prompt-cache", "cost", "latency", "coding-agent"]
weight: 13
---

[Prompt cache](/llm/knowledge-cards/prompt-cache/) 把重複 prefix 的計算結果在 LLM 服務端跨 request 持久化、後續 query 跳過 [prefill](/llm/knowledge-cards/prefill/) 階段。Anthropic / OpenAI / Bedrock / Gemini 都列為 cost 跟 [TTFT](/llm/knowledge-cards/ttft/) 的最大單一槓桿 — 90% cost 折扣 + 顯著 latency 改善。本章把 prompt caching 的運作機制、設計原則、coding agent / long-context 場景的 pattern、常見 anti-pattern 拆成可操作的工程實務。

注意三層 cache 概念的層次差異（[prompt cache 卡片](/llm/knowledge-cards/prompt-cache/) 有完整對比表）：[KV cache](/llm/knowledge-cards/kv-cache/) 是單次推論內、過去 token 的 K/V 暫存（autoregressive 才省重算）；[prefix cache](/llm/knowledge-cards/prefix-cache/) 是同一推論伺服器內跨 request 共用 KV cache；**prompt cache（本章聚焦）** 是雲端 LLM API 商業 feature、跨 request 跨時間、有 TTL。三者不同層、要區分。

## 本章目標

讀完本章後、你應該能：

1. 解釋 prompt cache 跟 [KV cache](/llm/knowledge-cards/kv-cache/) / [prefix cache](/llm/knowledge-cards/prefix-cache/) 的層次差異。
2. 對 coding agent / RAG / long-conversation 場景設計 cache breakpoint。
3. 估算自己應用開 prompt cache 的 cost / latency 收益。
4. 看到「cache 不命中」訊號時、能定位 anti-pattern 並修。

## Prompt cache 怎麼運作

LLM 推論的 prefill 階段對整個 prompt 算 KV cache、是長 prompt 的主要 latency 跟 compute 成本：

```text
無 cache：
  Request 1：[10K system prompt] + [tool schema 5K] + [user query 500] = 15.5K prefill
  Request 2：[10K system prompt] + [tool schema 5K] + [user query 700] = 15.7K prefill
  → 兩次都付 15K prefill 成本
```

開 prompt cache 後：

```text
Request 1：[10K system + 5K tool schema] | cache_control | + [user query 500]
  → 算出 prefix 的 KV cache、寫進服務端 cache（付 1.25× cost）
  → 後段 prefill 500 token

Request 2（5 分鐘內）：[10K system + 5K tool schema] | + [user query 700]
  → 服務端命中 cache、跳過 prefix 的 prefill（付 0.1× cost = 90% 折扣）
  → 只 prefill 700 token
  → TTFT 大幅降低
```

關鍵運作細節：

1. **Cache key = prefix 的 token sequence**：完全相同的 token sequence 才命中、差一個 token 就 miss
2. **TTL（time-to-live）**：cache 過一段時間（多數 5 min）自動失效、要 ext 1h 通常付額外 cost
3. **Write 比原價略貴、Read 大幅打折**：Anthropic 模型 write 1.25×、read 0.1×；OpenAI 模型 read 0.5×
4. **Minimum cacheable size**：通常 1K-4K token 起跳、短 prompt 不適合
5. **Cache 範圍**：跨 request、跨 conversation、跨 session、但同一 model + 同一 region

## Cache breakpoint 設計

Anthropic 用 `cache_control` 標記顯式 breakpoint、OpenAI 用自動偵測。但設計原則一致：**把不變的內容放 prefix、變動的放後面**。

典型 coding agent 的 prompt 結構：

```text
[1. System prompt]：agent 角色、規則、輸出格式             ← 不變
[2. Tool schema]：所有 tool 的 spec                       ← 不變（除非加新 tool）
[3. Skill registry / playbook]：known recipes              ← 半變（偶爾更新）
[4. Codebase context]：固定載入的核心檔案                  ← 半變
       ↓ cache_control breakpoint ↑
[5. Conversation history]：過去回合                       ← 變動
[6. Current user query]：當前 query                       ← 變動
[7. Current tool result]：剛跑完的 tool output             ← 變動
```

Breakpoint 放在「不變 vs 變動」交界處、讓 [1-4] 永遠 cache hit。

Anthropic 最多 4 個 breakpoint、可分層：

```text
breakpoint 1（最早）：[system prompt] → 永久 cache
breakpoint 2：       [+ tool schema] → 永久 cache
breakpoint 3：       [+ skill registry] → 半永久 cache
breakpoint 4（最晚）：[+ recent stable context] → 短期 cache
[後段]：             variable content（不 cache）
```

每個 breakpoint 各自命中 / miss、layered cache 讓「加新 skill」只 invalidate breakpoint 3 之後、不影響 breakpoint 1-2。

## 場景 1：Coding agent

Coding agent 是 prompt cache 命中區 — system prompt + tool schema 動輒 10K-30K token、每個 user turn 都重用。

收益估算（200K context 模型、10K scaffold、5K user query、3K answer）：

```text
無 cache：
  每 turn input cost = (10K + 5K) × $3/M = $0.045
  每 turn TTFT = 10K-15K prefill time（200-400ms）

開 cache：
  Turn 1（write）：(10K × 1.25 + 5K) × $3/M = $0.0525
  Turn 2-N（read）：(10K × 0.1 + 5K) × $3/M = $0.018
  TTFT：read 階段省掉 10K prefill、只剩 5K

10 turns 的累計 cost：
  無 cache：10 × $0.045 = $0.45
  開 cache：$0.0525 + 9 × $0.018 = $0.215
  → 節省 52%
```

長對話越長、cache 收益越大（cache write 是一次性成本）。

## 場景 2：RAG / long-context

RAG 場景把 retrieved chunks 放 prefix、user query 放後面、可以 cache retrieved chunks：

```text
[system prompt]
       ↓ breakpoint 1（system 永久 cache）
[retrieved chunks 來自 RAG]
       ↓ breakpoint 2（同 chunks 在 5min 內 cache）
[user query]
```

注意：每次 retrieval 不同 chunks 就 cache miss、所以 cache 適合「同個對話多輪、retrieval 結果穩定」、不適合「每 query 都 fresh retrieve」。

## 場景 3：Long document Q&A

讀者上傳 PDF / 文件、多輪問問題：

```text
[system prompt]
       ↓ breakpoint 1
[完整文件內容（可能 100K token）]
       ↓ breakpoint 2（文件永久 cache）
[user query]
```

第一次 query 付 1.25× 文件成本、後續 query 都 0.1×。100K 文件 + 10 個問題的場景下、節省極顯著（> 80% cost）。

## 常見 anti-pattern

1. **在 prefix 插入 timestamp / request-id**

```text
❌ System prompt: "你是 coding assistant、當前時間 2026-05-12 16:30:42、..."
   → 每秒不同 cache key、永遠 cache miss、付 1.25× write 不回本
✅ 把 timestamp 放後段、或省略（多數場景模型不需要精確時間）
```

2. **在 prefix 動態插入 user metadata**

```text
❌ System prompt: "User: alice@example.com, plan: premium、..."
   → 每個 user 不同 cache、命中率低
✅ User metadata 放後段、prefix 保持 user-agnostic
```

3. **Tool schema 順序不固定**

```text
❌ 每次 request 把 tool list 隨機 shuffle
   → 同樣 tool 但 token sequence 不同、cache miss
✅ Tool list 順序固定、新加 tool 都 append 到末尾
```

4. **太短的 prompt 也想 cache**

```text
❌ 500 token system prompt 開 cache
   → 多數服務商 minimum 1K-4K、不到門檻不 cache、且 write cost 不回本
✅ Cache 留給 > 1K 的 prefix、短 prompt 不必開
```

5. **混用 stream + cache 卻不檢查命中**

```text
❌ 開 cache 後不檢查 response 的 cache_read_input_tokens 欄位
   → 不知道實際命中率、可能 anti-pattern 已在燒 cost 沒察覺
✅ 監控 cache_read / cache_creation token 比例、低於 80% 命中率時 debug
```

## Cache miss 訊號跟診斷

訊號：

1. **Cost 比預期高**：應該命中的場景仍付 full price
2. **TTFT 沒改善**：cache hit 應該大幅降 TTFT、沒改善 = miss
3. **Response 的 usage 顯示 cache_read = 0**：直接訊號

診斷流程：

```text
1. 印出 raw request 的 prefix（cache_control 之前）
2. 比對連續兩次 request 的 prefix token sequence
3. 找出差異位置（diff）
4. 移除 / 重構讓兩次 prefix 完全相同
5. 跑 2-3 次 request、看 cache_read_input_tokens 是否上升
```

常見差異：timestamp、request id、user id、tool list 順序、retrieved chunks 順序、conversation summary 變動。

## 跟其他 cost 優化技巧的關係

| 技巧                                                               | 攻擊的 cost / latency 來源         | 跟 prompt cache 的關係                                   |
| ------------------------------------------------------------------ | ---------------------------------- | -------------------------------------------------------- |
| [Speculative decoding](/llm/knowledge-cards/speculative-decoding/) | Generation 階段 token cost         | 正交、可疊加                                             |
| [Batching](/llm/knowledge-cards/batching/)                         | Throughput per GPU                 | Production 才用、跟 prompt cache 都用                    |
| [Prefix cache](/llm/knowledge-cards/prefix-cache/)                 | 同 server 跨 request 共用 KV cache | 本地推論伺服器特性、prompt cache 是雲端 API 商業 feature |
| 模型量化                                                           | Generation tok/s                   | 正交、可疊加                                             |
| RAG 而非 long context                                              | Input token 量                     | RAG + cache 可同時用                                     |

## 本地推論伺服器有沒有類似機制

Ollama / LM Studio / llama.cpp 自身的 prompt cache：

| 工具      | 機制                                       | 範圍                             |
| --------- | ------------------------------------------ | -------------------------------- |
| llama.cpp | `--prompt-cache` flag、persistent file     | 重複跑同樣 prompt 時跳過 prefill |
| Ollama    | 內建 prefix cache、跨 request 共用         | 同 server 跨 request             |
| LM Studio | 同 Ollama 級別、視版本                     | 同上                             |
| vLLM      | 強 prefix cache（PagedAttention 設計支援） | 高併發 production                |

本地推論的 cache 主要靠 [prefix cache](/llm/knowledge-cards/prefix-cache/) 機制、跟雲端 API 的 prompt cache 商業 feature 同源、但定價 / TTL / 顯式 control 是雲端 API 才有的 product layer。

## 何時不適合用 prompt cache

1. **每 request prefix 必變**：streaming 任務、每 query 都帶 fresh 上下文
2. **Single-shot 對話**：用完就丟、沒有重複使用、write cost 不回本
3. **Prefix < 1K token**：不到 minimum、cache 不生效
4. **Cost 不敏感場景**：個人小流量、cache 設計 overhead 大於收益
5. **本地推論為主**：本地多用 prefix cache、prompt cache 是雲端 API 概念

## 何時過時 / 何時不過時

**不會過時的部分**：

- 「不變放 prefix、變動放後段」的設計原則
- Cache breakpoint 分層（system / tool schema / skill / context）
- Anti-pattern 分類（timestamp、user metadata、tool 順序）
- Cache miss 診斷流程

**會變的部分**：

- 各 vendor 的具體定價（write × / read × 折扣）
- TTL（5min vs 1h）的可選性跟價格
- Automatic vs explicit cache（OpenAI vs Anthropic 路線）
- Breakpoint 上限數量
- 本地推論伺服器的 cache 功能（持續演化）

## 小結

Prompt cache 是 cost / latency 的最大單一槓桿、coding agent / long-context / RAG / long-document Q&A 都是命中區。設計原則「不變放 prefix、變動放後段」、breakpoint 分層讓 invalidation 局部化。Anti-pattern（timestamp、user id、tool 順序、太短 prompt）會把 cache 變廢、診斷靠 cache_read_input_tokens 欄位。本地推論場景對應 prefix cache、機制同源但定價跟 control 是雲端 API 商業 feature。

下一章：[4.14 Agent memory 分層](/llm/04-applications/agent-memory-architecture/)、看 agent 如何在 context window 之外管理長期狀態。
