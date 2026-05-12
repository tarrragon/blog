---
title: "Prompt Cache"
date: 2026-05-12
description: "重複出現的 prompt prefix 在推論伺服器或 LLM 服務端被 cache、後續 query 跳過 prefill、大幅降 cost 跟 TTFT"
weight: 1
tags: ["llm", "knowledge-cards", "inference-optimization", "cost"]
---

Prompt cache 的核心概念是「**LLM 服務端 / 推論伺服器把重複出現的 prompt prefix（如 system prompt + tool schema）的 [KV cache](/llm/knowledge-cards/kv-cache/) 暫存起來、後續 query 跳過該 prefix 的 [prefill](/llm/knowledge-cards/prefill/) 階段**」。Anthropic / OpenAI / Bedrock / Gemini 都提供、最高 90% cost 折扣 + 13-31% [TTFT](/llm/knowledge-cards/ttft/) 改善、是 coding agent / long-context 應用的核心 cost / latency 槓桿。

## 概念位置

跟既有 cache 概念的層次：

| Cache 層                                           | 範圍                                         | 機制                                                |
| -------------------------------------------------- | -------------------------------------------- | --------------------------------------------------- |
| [KV cache](/llm/knowledge-cards/kv-cache/)         | 單一 conversation 的同一次推論               | 過去 token 的 K/V 暫存、autoregressive 才省重算     |
| [Prefix cache](/llm/knowledge-cards/prefix-cache/) | 多 request 共用 prefix（同 server 同 model） | 跨 request 共用 KV cache、production 推論伺服器特性 |
| **Prompt cache（本卡）**                           | 跨 request 跨時間、雲端 LLM API 服務端       | 服務端把 prefix 的 KV cache 持久化、有 TTL          |

Prompt cache 的「保留範圍」跟「定價」是商業 LLM 的 product feature：

| 服務                       | Cache TTL         | Write cost   | Read cost             | 觸發方式                            |
| -------------------------- | ----------------- | ------------ | --------------------- | ----------------------------------- |
| Anthropic（cache_control） | 5min 預設、1h ext | 1.25× 原價   | 0.1× 原價（90% 折扣） | 明確 cache_control breakpoint       |
| OpenAI                     | 自動（隱式）      | 同原價       | 0.5× 原價（50% 折扣） | 自動偵測重複 prefix（> 1024 token） |
| Bedrock（Anthropic）       | 5min              | 同 Anthropic | 同上                  | 同 Anthropic                        |
| Gemini                     | 自動 + explicit   | 視方案       | 視方案                | implicit + context caching API      |

> **事實查核註**：定價跟 TTL 隨時間更新、引用前以對應 vendor 當前文件為準。

## 設計責任

讀 LLM API docs / coding agent 設計 / cost optimization blog 看到「prompt cache」「context caching」「cache_control」就是這機制。寫 code 場景的判讀：

1. **誰最值得開**：coding agent（system prompt + tool schema 經常 > 10K token、每 turn 重用）、long-context RAG（檢索 chunks 重用）、long conversation（history 累積）
2. **設計原則**：把不變的內容（system prompt、tool schema、固定文件）放 prefix；變動的（user query、最新 file content）放後面
3. **常見 anti-pattern**：在 prefix 插入 timestamp / user-id / request-id → 每次 prefix 不同 → cache 從不命中、付 1.25× write cost 沒得回本
4. **5 分鐘 TTL 的意涵**：query 之間間隔 > 5 分鐘、cache 已 expire、要 1h ext TTL 才能撐長對話
5. **跟 [context budget](/llm/knowledge-cards/context-budget/) 的關係**：cache 攤平 scaffold 部分的 cost、所以可以放寬「scaffold ≤ 25%」的成本顧慮、focus 在「不超 context limit」即可
