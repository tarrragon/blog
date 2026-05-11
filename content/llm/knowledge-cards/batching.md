---
title: "Batching"
date: 2026-05-12
description: "多 request 一起跑、攤平 model load 成本：production LLM inference 的核心優化、決定 throughput vs latency 取捨"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Batching 的核心概念是「**多個 request 在同一個 forward pass 內一起跑、攤平 model weights 從記憶體讀到處理器的成本**」。是 production LLM inference 的核心優化——跟 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 瓶頸對接：讀一次 model weights、能 process N 個 request、單 request 的 effective throughput 上升 N 倍。

## 概念位置

Batching 介於 inference engine 內部、跟 [KV cache](/llm/knowledge-cards/kv-cache/) 一起決定一個 GPU / Apple Silicon 能服務多少並發 user。但 batching 不是 free——靜態 batching 要等湊滿才跑、延遲首字延遲；連續 batching 平衡 throughput + latency 但實作複雜。Single-user 場景常無 batching（local Mac 跑 Ollama 即此情境）、production multi-tenant 必有 batching。

## 可觀察訊號與例子

| 策略 | 機制 | 適合場景 |
| ---- | ---- | -------- |
| No batching | 每 request 獨立 forward pass | Single-user、極低 latency 要求 |
| Static batching | 等湊滿 N 個 request 才跑 | 高 throughput 批次處理（embedding pipeline、文件 ingest） |
| Continuous batching | 新 request 動態加入正在跑的 batch | vLLM / TGI / SGLang 等 production inference 主流 |
| In-flight batching | 不同 sequence 在不同 step 同時推 | NVIDIA Triton + TensorRT-LLM 等深度優化 |

實務觀察：production LLM 服務 throughput 在 batch size 4-32 之間有明顯提升、超過 GPU memory 上限後反而下降（KV cache 跟 model weight 競爭記憶體）。

## 設計責任

選 batching 策略看兩維度：

1. **應用 latency tolerance**：
    - 互動式 UI（chatbot、IDE 補完）→ continuous batching、低 latency 優先
    - 批次處理（夜間 summarization）→ static batching、throughput 優先
2. **硬體 KV cache 上限**：
    - GPU memory - model weights = batchable 容量
    - 預估 max batch size = available_memory / per_user_kv_cache

Embedding 服務通常 batch 16-128 都 OK（embedding 是純 forward pass、無 KV cache 累積）；chat / generation 服務 batch size 受 KV cache 嚴格限制。

詳細跟 production 部署 capacity planning 的對接見 [4.5 Production 資源評估](/llm/04-applications/production-resource-planning/)；跟 [autoregressive](/llm/knowledge-cards/autoregressive/) 推論的單 token 瓶頸對應的優化討論見 [3.2 attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)。
