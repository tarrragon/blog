---
title: "QLoRA"
date: 2026-05-12
description: "把 base model 量化到 4-bit + LoRA fine-tune 的組合、消費級 GPU 也能 fine-tune 大模型"
weight: 1
tags: ["llm", "knowledge-cards", "fine-tuning", "quantization"]
---

QLoRA（Quantized LoRA、Dettmers et al., 2023）的核心概念是「**把 base model 量化到 4-bit（凍住）+ 用 [LoRA](/llm/knowledge-cards/lora/) 訓兩個小矩陣**」。讓消費級 GPU（24GB VRAM）就能 fine-tune 30B-70B 模型、是現代 local fine-tuning 主流。

## 跟其他概念的關係

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

## 判斷條件與後果

QLoRA 是否適用，由手上的 VRAM、可接受的品質差距與 fine-tune 之後的推論方式決定（讀 Hugging Face PEFT 文件看到「QLoRA」「bnb-4bit」指的就是這個方法）：

1. **VRAM 只有消費級 GPU 的容量時**，BF16 base 的 LoRA 在 7B 以上就放不下，因為 base 權重本身佔掉大部分記憶體；QLoRA 把 base 壓到 4-bit，同一張 24GB 的卡可以 fine-tune 30B 上下的模型（上表 30–32B 約 20–24GB）。
2. **估算 VRAM 時**，QLoRA 訓 N B 參數的模型約需 `0.6 × N` GB（30B 約 18GB、70B 約 42GB）。估出來的值超過手上顯卡的容量時，這張卡訓不了這個大小的模型，選項只剩換較小的模型或改用多卡。
3. **品質要求接近 full fine-tune 時**，QLoRA 合併權重後的模型實測跟 full fine-tune 的差距在 2–3% 以內；能接受這個差距的場景，用不著 full fine-tune 的多卡 H100 成本。
4. **跟 [LoRA](/llm/knowledge-cards/lora/) 的分界在 base 是否量化**：LoRA 的 base 維持 BF16，QLoRA 的 base 量化到 4-bit，兩者訓的都是 LoRA 的 A、B 矩陣，所以 QLoRA 是 LoRA 的延伸，不是另一種 adapter。
5. **推論時保留 4-bit base 再載入 LoRA adapter 時**，記憶體用量維持在 4-bit 的水準，每次 forward 都要先 dequantize base；merge 之後轉成 GGUF Q4_K_M 時，模型大小跟 base 的 Q4_K_M 相同，推論時不必另外載入 adapter。
