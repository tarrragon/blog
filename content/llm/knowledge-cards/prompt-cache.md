---
title: "Prompt Cache"
date: 2026-05-12
description: "重複出現的 prompt prefix 在推論伺服器或 LLM 服務端被 cache、後續 query 跳過 prefill、大幅降 cost 跟 TTFT"
weight: 1
tags: ["llm", "knowledge-cards", "inference-optimization", "cost"]
---

Prompt cache 的核心概念是「**LLM 服務端 / 推論伺服器把重複出現的 prompt prefix（如 system prompt + tool schema）的 [KV cache](/llm/knowledge-cards/kv-cache/) 暫存起來、後續 query 跳過該 prefix 的 [prefill](/llm/knowledge-cards/prefill/) 階段**」。Anthropic / OpenAI / Bedrock / Gemini 都提供、最高 90% cost 折扣 + 13-31% [TTFT](/llm/knowledge-cards/ttft/) 改善、是 coding agent / long-context 應用的核心 cost / latency 槓桿。

## 跟其他概念的關係

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

## 判斷條件與後果

Prompt cache 的折扣有兩個前提：後續 request 的 prefix 跟寫入 cache 時逐 token 相同，而且兩次 request 的間隔還在 TTL 之內。一個應用是否值得開、prompt 的內容怎麼排，都由這兩個前提推得出來：

1. **prefix 很長而且每一輪重複出現時**（coding agent 每一輪都帶 system prompt 與 tool schema，常超過 10K token；long-context RAG 重複帶同一批 chunk；長對話每一輪重送累積的 history），每一輪都省掉這段 prefix 的 prefill，費用與 TTFT 的節省隨 prefix 長度放大。prefix 短的應用付了寫入的成本，讀取省下的量很少。
2. **變動的內容（user query、最新的 file content）排在不變的內容之前時**，prefix 從變動的那個 token 起就跟上一次不同，排在後面的 system prompt 與 tool schema 也讀不到 cache，原因是 cache 比對的是從開頭起連續相同的 token；所以不變的內容排在前面，變動的排在後面。
3. **prefix 裡夾著每次都不同的值時**（timestamp、user-id、request-id），每個 request 的 prefix 都不同，cache 一次都不命中；在 Anthropic 這類寫入加價的服務上，每次寫入付 1.25 倍的價格而沒有任何一次讀取回本，總成本比不開 cache 還高。
4. **兩次 request 的間隔超過 TTL 時**（Anthropic 預設 5 分鐘），cache 已經過期，下一個 request 重新付寫入的成本。使用者常停頓超過 5 分鐘的長對話，用 1 小時的延長 TTL 才讀得到前一輪的 cache。
5. **scaffold 的 token 大多由 cache 讀取時**，這些 token 的費用降到讀取價，[context budget](/llm/knowledge-cards/context-budget/) 裡「scaffold ≤ 25%」的成本理由跟著變弱，剩下的限制是總長度不超過 context window。
