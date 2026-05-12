---
title: "VRAM"
date: 2026-05-12
description: "顯卡上的記憶體、跟系統 RAM 是兩塊獨立預算、決定能載入多大模型權重跟 KV cache"
weight: 1
tags: ["llm", "knowledge-cards", "hardware", "memory"]
---

VRAM（Video RAM）的核心概念是「顯卡晶片上的高速記憶體、跟系統主機板上的 RAM 是物理上獨立的兩塊預算」。獨立 GPU 場景下、模型權重要載入 VRAM 才能用 GPU 高速計算；VRAM 容量直接決定能跑多大模型。跟 Apple Silicon 的 [統一記憶體](/llm/knowledge-cards/unified-memory/) 不同、PC 上 VRAM 跟系統 RAM 兩塊預算要分開規劃。

## 概念位置

VRAM 同時影響「能載入什麼」跟「跑多快」兩個維度：

1. **容量**（GB）：決定能放多少模型權重 + [KV cache](/llm/knowledge-cards/kv-cache/) + 推論中間結果。容量不夠則跑不起來、需透過 [MoE CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/) 把部分權重放系統 RAM。
2. **頻寬**（GB/s）：影響每 token 生成速度上限、見 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 卡片。

常見消費級 GPU 的 VRAM 規格（廠商標稱、依世代與型號變化）：

| GPU                   | VRAM 容量 | VRAM 類型 |
| --------------------- | --------- | --------- |
| RTX 5060 / 4060       | 8GB       | GDDR6/7   |
| RTX 5060 Ti / 4060 Ti | 16GB      | GDDR6/7   |
| RTX 5070 Ti / 4070 Ti | 16GB      | GDDR6/7   |
| RTX 4090              | 24GB      | GDDR6X    |
| RTX 5090              | 32GB      | GDDR7     |

VRAM 容量是選 GPU 跑本地 LLM 的第一決策軸、頻寬是第二決策軸。同容量下、頻寬接近 2 倍的卡（如 5070 Ti 對 5060 Ti）生字速度差異明顯。

> **事實查核註**：上表是 2026 年 5 月主流消費級 NVIDIA GPU 規格的數量級對照、實際 VRAM 容量、頻寬、GDDR 版本依特定型號、廠商 / SKU、製造時間變化、引用前以 [NVIDIA 官方規格頁](https://www.nvidia.com/en-us/geforce/graphics-cards/) 為準。

## 設計責任

理解 VRAM 後可以解釋三個現象：為什麼同樣 16GB 容量、不同卡的生字速度差很多（頻寬不同）；為什麼 MoE 模型在 16GB VRAM 上跑得了 30B 級模型（透過卸載）；為什麼 [PCIe](/llm/knowledge-cards/pcie/) 頻寬在 PC 場景影響 MoE 卸載的速度（系統 RAM 跟 VRAM 之間的橋）。

選 PC 規劃本地 LLM 時、VRAM 容量決定能跑的模型上限、VRAM 頻寬決定生字速度上限、系統 RAM 容量決定 MoE 卸載空間。詳見 [5.0 VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/)。
