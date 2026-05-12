---
title: "Learning Rate"
date: 2026-05-12
description: "gradient descent 每步更新權重的幅度、訓練中最敏感的 hyperparameter"
weight: 1
tags: ["llm", "knowledge-cards", "training"]
---

Learning rate（學習率、lr、α、η）的核心概念是「[gradient](/llm/knowledge-cards/gradient/) 每步更新權重時、被乘上的純量縮放因子」。更新公式 `W_new = W_old - lr × gradient` 裡的 lr 就是它。是訓練最敏感的單一 hyperparameter — 太大會 diverge（loss 飛走）、太小會訓得超慢或卡 local minimum。

## 概念位置

LLM 訓練 learning rate 的常見模式：

| 階段                                                                  | 典型 lr     | 理由                                          |
| --------------------------------------------------------------------- | ----------- | --------------------------------------------- |
| [Pre-training](/llm/knowledge-cards/pre-training/)                    | 1e-4 ~ 3e-4 | 訓 trillion token、需要溫和的 lr 避免 diverge |
| [SFT](/llm/knowledge-cards/sft/)                                      | 1e-5 ~ 5e-5 | base model 已收斂、用小 lr 微調避免 overshoot |
| [RLHF](/llm/knowledge-cards/rlhf/) / [DPO](/llm/knowledge-cards/dpo/) | 1e-7 ~ 1e-6 | 又比 SFT 更小、避免破壞 SFT 學到的對話能力    |
| [LoRA](/llm/knowledge-cards/lora/) fine-tune                          | 1e-4 ~ 5e-4 | 只訓小 adapter、可用較大 lr                   |

Learning rate schedule（lr 隨訓練步數調整）的主流模式：

1. **Warmup**：訓練最初幾百 ~ 幾千 step、lr 從 0 線性升到目標值。避免初期 gradient 大、模型瞬間 diverge。
2. **Cosine decay**：warmup 後、lr 用 cosine 函數從目標值降到接近 0。訓練後期細調。
3. **WSD（Warmup-Stable-Decay）**：近期變體、中間維持高 lr 更久。

## 設計責任

讀 training config 看到 `learning_rate`、`lr_scheduler_type: cosine`、`warmup_steps: 1000` 等就是這組設定。Fine-tune 時 lr 設太大、模型會「忘記」pre-training 學到的能力（catastrophic forgetting）；太小則訓不進新資料、loss 不降。實務除錯：fine-tune 時 loss 第一個 epoch 就 NaN、十之八九是 lr 太大；loss 完全不降、十之八九是 lr 太小或 [gradient](/llm/knowledge-cards/gradient/) 沒流到要訓的權重。
