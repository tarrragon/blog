---
title: "GPU Compute Backend"
date: 2026-05-12
description: "GPU 加速計算的底層 API 介面（CUDA / ROCm / Vulkan / Metal / SYCL）、決定推論軟體能否用 GPU 跑得快"
weight: 1
tags: ["llm", "knowledge-cards", "hardware", "gpu", "cuda", "rocm"]
---

GPU compute backend 的核心概念是「推論軟體（如 llama.cpp、PyTorch）跟 GPU 之間的計算 API 抽象層」。不同廠商 GPU 對應不同 backend、同一推論軟體通常要為每個 backend 編譯獨立 build。選對 backend 直接影響 GPU 算力能否被有效利用。

## 概念位置

各家 GPU 對應的常見 backend（2026 年 5 月狀態、依社群實踐變化）：

| Backend  | 主要 GPU 廠商     | 平台支援                 | llama.cpp 生態成熟度 |
| -------- | ----------------- | ------------------------ | -------------------- |
| CUDA     | NVIDIA            | Windows / Linux          | 最成熟、社群預設     |
| ROCm     | AMD               | Linux 主、Windows 演進中 | 中、依 GPU 型號變化  |
| Vulkan   | 跨廠商通用        | Windows / Linux          | 中、通用 fallback    |
| Metal    | Apple Silicon     | macOS                    | 成熟（屬模組一範圍） |
| SYCL     | Intel ARC         | Windows / Linux          | 相對年輕             |
| DirectML | 多廠商（DirectX） | Windows                  | 較少用於 LLM         |
| OpenVINO | Intel             | 多平台                   | 偏 Intel 生態        |

選 backend 的判讀依硬體跟平台：NVIDIA GPU 用 CUDA、AMD on Linux 優先 ROCm、AMD on Windows 多用 Vulkan、Intel ARC 用 Vulkan 或 SYCL、Apple Silicon 用 Metal。

> **事實查核註**：上表的「llama.cpp 生態成熟度」是社群常見回報、不是經本卡系統實測的 benchmark；各 backend 的支援度跟 throughput 依推論軟體版本快速演進、引用前以對應 backend 的官方文件跟 [llama.cpp release notes](https://github.com/ggml-org/llama.cpp/releases) 為準。

## 設計責任

理解 GPU compute backend 後可以解釋三個現象：為什麼下載 llama.cpp release 要選 CUDA / ROCm / Vulkan 版本（每個 build 對應一種 backend）、為什麼同樣硬體 throughput 差很多（backend 不對或 fallback 到 CPU）、為什麼非 NVIDIA GPU 跑 LLM 經驗較少（CUDA 生態太成熟、其他 backend 仍在演進）。

選 PC GPU 跑本地 LLM 時、backend 成熟度是「工具鏈支援度」軸、跟硬體規格軸獨立、選卡時兩軸都要考慮。詳見 [5.6 GPU 廠商差異](/llm/05-discrete-gpu/gpu-vendor-differences/)。
