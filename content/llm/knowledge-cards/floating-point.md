---
title: "Floating Point（FP32 / FP16 / BF16）"
date: 2026-05-12
description: "fp32 / fp16 / bf16 浮點格式的位元結構與 LLM 訓練 / 推論的精度取捨"
weight: 1
tags: ["llm", "knowledge-cards", "numerical-precision", "math"]
---

Floating point（浮點數）的核心概念是「**用「符號位 + 指數位 + 尾數位」表示實數的二進制格式**」。LLM 訓練跟推論用的精度（fp32 / bf16 / fp16）就是不同的位元分配方案。理解這些差異能解釋為什麼 bf16 是訓練主流、為什麼 [量化](/llm/knowledge-cards/quantization/) 對品質的影響不是「越多 bit 越好」這麼簡單。

## 概念位置

主流浮點格式的位元分配：

| 格式              | 總 bit | 符號位 | 指數位 | 尾數位 | 動態範圍                | 精度（有效位數） |
| ----------------- | ------ | ------ | ------ | ------ | ----------------------- | ---------------- |
| FP32              | 32     | 1      | 8      | 23     | ±10^38                  | 7 位             |
| FP16              | 16     | 1      | 5      | 10     | ±65504（容易 overflow） | 4 位             |
| BF16              | 16     | 1      | 8      | 7      | ±10^38（同 fp32）       | 3 位             |
| FP8 (E4M3 / E5M2) | 8      | 1      | 4 / 5  | 3 / 2  | 視變體                  | 1-2 位           |

關鍵 trade-off：

1. **FP16 精度好、範圍窄**：尾數多、表達小範圍內細節準；但指數少、容易 overflow（gradient 爆炸時）/ underflow（gradient 接近 0 時）。
2. **BF16 範圍跟 fp32 一樣大、精度差**：指數位跟 fp32 同（8 位）、訓練時的 dynamic range 跟 fp32 接近、不會 overflow；但尾數少、精度差。實測對訓練影響小、所以是現代 LLM 訓練主流。
3. **FP8 是新興格式**：H100 / B200 等新 GPU 原生支援、訓練 / 推論都能加速、但精度損失需要 careful loss scaling。

LLM 工作流的精度選擇：

| 場景                   | 主流精度                                                             |
| ---------------------- | -------------------------------------------------------------------- |
| Pre-training（大模型） | BF16 + 部分 FP32（如 optimizer state）                               |
| Fine-tuning            | BF16 + 可選 FP8 / Q4（QLoRA）                                        |
| 推論（雲端 high-end）  | FP16 / BF16                                                          |
| 推論（消費級本機）     | Q4_K_M 等量化、見 [quantization](/llm/knowledge-cards/quantization/) |

## 設計責任

讀 paper / config 看到 `mixed_precision: bf16`、`torch_dtype: bfloat16` 就是 BF16 訓練。寫 code 場景的判讀：本機跑 [GGUF](/llm/knowledge-cards/gguf/) Q4_K_M 模型、內部運算的 activation 仍是 fp16 / bf16、只有權重儲存是 4-bit；[KV cache](/llm/knowledge-cards/kv-cache/) 預設也是 fp16、量化 KV cache 是進階優化（K=Q8 / V=Q4）。
