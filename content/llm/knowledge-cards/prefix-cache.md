---
title: "Prefix Cache"
date: 2026-05-12
description: "把多個請求共用的前綴 prompt 的 KV cache 重用、省下重複 prefill 算力的優化、production 多用戶服務的常見設計"
weight: 1
tags: ["llm", "knowledge-cards", "kv-cache", "optimization", "production"]
---

Prefix Cache 的核心概念是「當多個請求共用相同的前綴 prompt（如同一 system prompt、同一 few-shot 範例）、把該前綴的 [KV cache](/llm/knowledge-cards/kv-cache/) 算一次、後續請求共用、省下重複 [prefill](/llm/knowledge-cards/prefill/) 算力」。是 production LLM 服務的常見優化、能大幅降低 latency 跟成本；但在多租戶場景下、跨租戶共用 prefix cache 是直接的隱私洩漏面。

## 概念位置

Prefix Cache 在推論流程中的角色：

```text
傳統推論：
  Request A：system prompt + user A → 完整 prefill → 生成
  Request B：system prompt + user B → 完整 prefill → 生成
                                       ↑ 重複算 system prompt

開啟 Prefix Cache：
  Request A：system prompt + user A → prefill 整段、cache 共用 prefix
  Request B：system prompt + user B → 重用 cache 的 system prefix + 只 prefill user B → 生成
                                       ↑ 省下 system prompt 的 prefill 算力
```

效益對應的場景：

| 場景                                | 效益               |
| ----------------------------------- | ------------------ |
| 同 system prompt、不同 user message | prefill 算力大幅省 |
| 同 few-shot 例子、不同 query        | prefill 算力大幅省 |
| 長 RAG context 共用、不同問題       | prefill 算力大幅省 |
| 完全獨立的請求（無共用前綴）        | 無效益             |

主流[推論引擎](/llm/knowledge-cards/inference-server/)的支援度（依版本變化）：vLLM、SGLang、llama.cpp 等都有 prefix cache 機制、命名各異。

> **事實查核註**：prefix cache 的命名、設定方式、tenant 隔離預設行為依推論引擎跟版本差異大、引用前以對應引擎的官方文件為準（如 [vLLM Automatic Prefix Caching](https://docs.vllm.ai/)、SGLang RadixAttention 等）。

## 設計責任

理解 prefix cache 後可以解釋兩個現象：為什麼 production LLM 服務的 latency 在啟用 prefix cache 後大幅下降（system prompt 不再每次重算）、為什麼 prefix cache 在多租戶場景是隱私風險（A 租戶的 prefix 可能被 B 看到、見 [llm-multi-tenant-isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)）。

production 設計時、prefix cache 應該按 tenant 分桶、同 tenant 內可共用、跨 tenant 必須隔離。隔離邊界對齊 [tenant-boundary](/backend/knowledge-cards/tenant-boundary/) 卡片的設計。
