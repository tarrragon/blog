---
title: "oMLX"
date: 2026-05-14
description: "以 MLX 為基礎、針對 Apple Silicon 長 context 與 SSD KV cache 優化的本地推論伺服器路線"
weight: 1
tags: ["llm", "knowledge-cards", "mlx", "inference-server"]
---

oMLX 的核心概念是「**以 MLX 為基礎、針對 Apple Silicon 長 context 場景優化的推論伺服器路線**」。它不是 [MLX](/llm/knowledge-cards/mlx/) 這個運算框架本身，也不是 [MTP](/llm/knowledge-cards/mtp/) 這類解碼技巧，而是把 MLX serving、長 context 與 KV cache 管理組合成服務層能力。

## 概念位置

oMLX 位在 [three-layer architecture](/llm/knowledge-cards/three-layer-architecture/) 的伺服器層。它的差異化重點通常是 Apple Silicon 最佳化、長 context prefill 成本、SSD-backed KV cache 或相關 cache 策略；它對上仍可提供 API，對下仍載入模型權重。

## 可觀察訊號與例子

看到文章把 oMLX 跟 Ollama、LM Studio、llama.cpp server 放在同一組比較時，討論的是 serving 路線。看到它跟 MLX / MTP 並列時，判讀重點是「框架、解碼技巧、伺服器」三者層級不同。

## 設計責任

評估 oMLX 時，重點是工作流是否真的受長 context 與 [TTFT](/llm/knowledge-cards/ttft/) 影響；短 prompt 對話通常未必需要特化 serving。下一步路由是 [MLX](/llm/knowledge-cards/mlx/)、[KV Cache](/llm/knowledge-cards/kv-cache/) 與 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)。
