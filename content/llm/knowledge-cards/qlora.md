---
title: "QLoRA"
date: 2026-05-12
description: "把 base model 量化到 4-bit + LoRA fine-tune 的組合、消費級 GPU 也能 fine-tune 大模型"
weight: 1
tags: ["llm", "knowledge-cards", "fine-tuning", "quantization"]
---

QLoRA（Quantized LoRA、Dettmers et al., 2023）的核心概念是「**把 base model 量化到 4-bit（凍住）+ 用 [LoRA](/llm/knowledge-cards/lora/) 訓兩個小矩陣**」。讓消費級 GPU（24GB VRAM）就能 fine-tune 30B-70B 模型、是現代 local fine-tuning 主流。

## 概念位置

QLoRA vs full fine-tuning vs LoRA 的記憶體需求對比（70B 模型）：

| 方法             | Base model 精度 | 訓練記憶體 | 適合硬體                     |
| ---------------- | --------------- | ---------- | ---------------------------- |
| Full fine-tuning | BF16            | ~280 GB    | 多卡 H100                    |
| LoRA             | BF16            | ~150 GB    | 多卡 A100 / H100             |
| **QLoRA**        | 4-bit (NF4)     | **~40 GB** | 單張 A100 80GB / 雙 24GB GPU |
| QLoRA on 7B      | 4-bit           | ~6-8 GB    | 消費級 16GB+ GPU             |
| QLoRA on 30-32B  | 4-bit           | ~20-24 GB  | 消費級 24GB+ GPU（5090）     |

QLoRA 的核心創新（簡化）：

1. **4-bit NormalFloat（NF4）量化**：base model 用 4-bit 表示、精度損失低於原 INT4
2. **Double quantization**：量化常數本身也量化、再省一點記憶體
3. **Paged optimizer**：optimizer state 跑 CPU offload、避免訓練 spike OOM
4. **LoRA on 4-bit base**：[LoRA](/llm/knowledge-cards/lora/) 訓的 A、B 矩陣仍是 BF16、只有 base 是 4-bit、推論時 dequantize → 加 LoRA → forward

## 設計責任

讀 fine-tuning 教學 / Hugging Face PEFT 文件看到「QLoRA」「bnb-4bit」就是這方法。寫 code 場景的判讀：

1. **想 fine-tune 大模型在消費級硬體**：QLoRA 是 default 選擇（不用 QLoRA、就只能訓 < 7B）
2. **記憶體預算估算**：QLoRA 訓 N B 模型約需 `0.6 × N GB` VRAM（30B → ~18GB、70B → ~42GB）
3. **品質 vs full fine-tune 差距**：QLoRA 後合併權重的模型、實測跟 full fine-tune 接近（差距 < 2-3%）、對多數場景可接受
4. **跟 [LoRA](/llm/knowledge-cards/lora/) 卡片區分**：純 LoRA 是「base 不量化、訓 LoRA」、QLoRA 是「base 量化 4-bit、訓 LoRA」；QLoRA 是 LoRA 的延伸、不是替代
5. **推論時的選擇**：QLoRA fine-tuned 模型可以「base 仍 4-bit + 載入 LoRA adapter」推論、記憶體用量低；也可以 merge 後用 GGUF Q4_K_M、跟 base 原相同
