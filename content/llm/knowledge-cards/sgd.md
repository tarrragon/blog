---
title: "SGD"
date: 2026-05-12
description: "Stochastic Gradient Descent：每次用 mini-batch 算 gradient 更新權重的基礎 optimizer"
weight: 1
tags: ["llm", "knowledge-cards", "training", "optimizer"]
---

SGD（Stochastic Gradient Descent、隨機梯度下降）的核心概念是「每次只用一小批資料（mini-batch）算 [gradient](/llm/knowledge-cards/gradient/)、更新權重」。對比的是 vanilla gradient descent（用全部資料算一次 gradient）：full-batch 在 trillion-token 級資料下完全不可行、SGD 用 mini-batch 把記憶體跟計算成本拉到可行範圍。

## 概念位置

SGD 的更新公式：

```text
W_new = W_old - learning_rate × gradient_of_loss_on_minibatch
```

跟其他 optimizer 的對比：

| Optimizer                                        | 更新規則                                         | 特性                           |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------ |
| SGD                                              | `W -= lr × g`                                    | 簡單、慢、容易卡 local minimum |
| SGD + Momentum                                   | 加速度項：`v = μv + g; W -= lr × v`              | 衝過 saddle point、收斂較穩    |
| [Adam / AdamW](/llm/knowledge-cards/adam-adamw/) | 對每個參數自適應 lr、用 gradient 的 EMA 跟二階矩 | 對 lr 較不敏感、LLM 訓練主流   |

LLM 訓練幾乎都用 Adam / AdamW、不是純 SGD。但 SGD 仍出現在：

1. **小模型 / 簡單任務**：fine-tune 小 vision 模型、SGD + momentum 仍是合理選擇。
2. **理論分析 / 教學**：SGD 是最簡單的 optimizer、用來解釋 gradient descent 概念。
3. **某些 fine-tuning 場景**：[LoRA](/llm/knowledge-cards/lora/) 或 SFT 偶爾用 SGD（避免 Adam 改變 base model 太多）。

## 設計責任

讀 paper / training script 看到 optimizer 選擇、SGD 是基線、其他 optimizer 通常是「對 SGD 的改進」。寫 code 場景的判讀：訓練自己的小模型可以從 SGD + momentum 開始；fine-tune 大 LLM 沒理由不用 AdamW。
