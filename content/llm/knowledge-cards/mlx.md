---
title: "MLX"
date: 2026-05-11
description: "Apple 釋出的 Apple Silicon 數值運算 framework：類似 PyTorch / JAX 的 Mac 對應物"
weight: 1
tags: ["llm", "knowledge-cards"]
---

MLX（Machine Learning eXchange）的核心概念是「Apple 為 Apple Silicon 設計的數值運算 framework」，2023 年由 Apple 釋出。它提供 Python API、自動排程 CPU / GPU / Neural Engine、利用[統一記憶體架構](/llm/knowledge-cards/unified-memory/)避免在不同記憶體層之間搬資料。

## 概念位置

MLX 屬於基底設施層、跟 PyTorch、JAX、NumPy 並列、是「跑神經網路用的底層數值庫」。它本身不是[推論伺服器](/llm/knowledge-cards/inference-server/)、不是模型、也不是加速技巧；上層工具站在 MLX 這塊地基上做封裝。

| 通用世界      | Apple 世界                     |
| ------------- | ------------------------------ |
| PyTorch / JAX | MLX                            |
| CUDA          | Metal（MLX 在 GPU 上經 Metal） |
| NumPy         | `mlx.core`                     |
| Transformers  | `mlx-lm`、`mlx-community`      |

## 可觀察訊號與例子

直接用 MLX 跑模型：

```bash
pip install mlx-lm
mlx_lm.generate --model mlx-community/Llama-3.2-3B-Instruct-4bit --prompt "hi"
```

這段命令會載入 MLX format 權重、用 MLX framework 在 Apple Silicon 上跑推論。需要再 wrap 成 HTTP server 才能讓 IDE 連、`mlx_lm.server` 是輕量選擇、oMLX 是建在 MLX 之上的完整推論伺服器。

## 設計責任

寫 code 場景的多數使用者透過 Ollama（用 llama.cpp 當引擎、跟 MLX 無關）、體驗已足夠。直接用 MLX 適合三種情境：想跑 Apple 釋出的 MLX format 模型、想用 MLX 寫研究 code、想試 MLX backend 的推論伺服器（oMLX）。看到「Ollama 用 MLX 加速」這類說法時、回到本卡確認 Ollama 內部 backend 是 llama.cpp 而非 MLX。
