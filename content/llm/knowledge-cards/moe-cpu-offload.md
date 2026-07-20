---
title: "MoE CPU Offload（CPU 卸載）"
date: 2026-05-12
description: "把 Mixture-of-Experts 模型不活躍的專家層權重放在系統 RAM、用到再走 PCIe 拉回 GPU、讓有限 VRAM 跑得了更大模型"
weight: 1
tags: ["llm", "knowledge-cards", "moe", "discrete-gpu", "memory"]
---

MoE CPU 卸載的核心概念是「[Mixture-of-Experts](https://en.wikipedia.org/wiki/Mixture_of_experts) 模型每個 token 只啟用少數專家、把不活躍的專家權重留在系統 RAM、用到再走 PCIe 拉回 GPU」。它讓 16GB VRAM 卡能載入 30B / 70B 等級的 MoE 模型、是 [獨立 GPU 場景](/llm/05-discrete-gpu/) 相對 [統一記憶體](/llm/knowledge-cards/unified-memory/) 場景多出的工程選項。

## 概念位置

MoE 卸載屬於「推論時的權重位置管理」、跟 [量化](/llm/knowledge-cards/quantization/) 屬於「權重精度壓縮」是兩個獨立維度、可以疊加（如 30B MoE Q4 + 卸載部分層、模型精度跟記憶體位置同時被處理）。它跟 [KV cache](/llm/knowledge-cards/kv-cache/) 量化是 PC 場景常一起使用的兩個工具：卸載騰出 VRAM、KV cache 量化讓騰出的 VRAM 拿去開大 [context window](/llm/knowledge-cards/context-window/)。

在 llama.cpp 中、對應的旗標是 `--n-cpu-moe <N>`、把 N 層的 MoE 專家權重保留在 CPU 記憶體。例如 `--n-cpu-moe 30` 表示 30 層的專家層留 RAM、其餘走 GPU。

## 可觀察訊號與例子

以 Qwen3-30B-A3B Q4_K_M（模型體積 10 GB 級、active parameter 約 3B 等級）為例、不同卸載策略下記憶體分布與生字速度的相對方向（具體數值依驅動、CUDA backend、模型版本、PCIe 版本變化、本表用於說明趨勢、不是嚴格 benchmark）：

| 配置      | 卸載策略          | VRAM 佔用方向  | RAM 佔用方向    | 生字速度方向（同卡比較） |
| --------- | ----------------- | -------------- | --------------- | ------------------------ |
| 全載 VRAM | `--n-cpu-moe 0`   | 接近 VRAM 上限 | 系統正常        | 上限取決於 VRAM 頻寬     |
| 中度卸載  | `--n-cpu-moe ~20` | 顯著下降       | 上升至 10 GB 級 | 較全載小幅下降           |
| 重度卸載  | `--n-cpu-moe ~30` | 大幅下降       | 上升較多        | 較全載明顯下降           |
| 極限卸載  | `--n-cpu-moe ~40` | 接近最低       | 上升最多        | 較全載大幅下降           |

> **事實查核註**：上表是趨勢示意、不是經本文系統實測的數值。實際數值依顯卡型號、PCIe 版本、CUDA backend、GGUF 量化版本、`-ngl` 設定、context 長度與 batch size 變化、建議用 `llama-bench` 或實際工作流校準。

社群常見的觀察是：MoE 卸載對生字速度的衰減幅度、相對於「Dense 模型把同樣比例的層卸載到 CPU」較小、原因是 MoE 每 token 只啟用少數專家、PCIe 上的權重傳輸量也較少；具體幅度依模型架構（active parameter 比例、專家數）變化。

## 設計責任

理解 MoE 卸載後、可以解釋三個 PC 場景的現象：16GB VRAM 卡能載入 30B 級 MoE 模型（透過部分卸載而非全載 VRAM）、PC 場景 64GB RAM 相對 32GB 在 MoE 卸載空間上明顯更寬裕（可卸載更多層）、Mac 統一記憶體場景較少需要「卸載」這個概念（VRAM 跟 RAM 共用、不需要在兩個區域之間搬資料）。

設定 PC 推論伺服器時、卸載層數通常跟 KV cache 量化、context 長度、併發數一起調：先估算想開的 context 長度、扣掉 KV cache 體積算出 VRAM 餘量、再選卸載層數讓模型剛好放得進。詳見 [5.0 VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/)。
