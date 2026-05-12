---
title: "Gradient Explosion / Vanishing"
date: 2026-05-12
description: "深層網路訓練中 gradient 透過 chain rule 累乘、容易爆炸或衰減到 0 的兩種失敗模式"
weight: 1
tags: ["llm", "knowledge-cards", "training", "math"]
---

Gradient explosion（爆炸）跟 gradient vanishing（消失）的核心概念是「深層網路的 [backpropagation](/llm/knowledge-cards/backpropagation/) 透過 chain rule 一層層相乘、若每層 gradient > 1、累乘到輸入層會指數爆炸；若每層 gradient < 1、累乘到輸入層會衰減到接近 0」。兩者是深層網路訓不起來的典型病因、現代 Transformer 用 [residual connection](/llm/knowledge-cards/residual-connection/) + [layer normalization](/llm/knowledge-cards/layer-normalization/) 解決。

## 概念位置

兩種失敗模式的訊號跟處理：

| 模式               | 訊號                                   | 主要成因                                                                               | 處理                                                                                                                                                               |
| ------------------ | -------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Gradient explosion | loss 突然變 NaN、gradient norm > 1000+ | [Learning rate](/llm/knowledge-cards/learning-rate/) 太大、初始化不當、loss 函數有奇點 | Gradient clipping（截斷 norm 上限、如 1.0）、降低 lr、檢查資料 outliers                                                                                            |
| Gradient vanishing | 深層權重幾乎不更新、loss 卡 plateau    | 層數深、activation 飽和區（sigmoid、tanh）、缺 skip connection                         | [Residual connection](/llm/knowledge-cards/residual-connection/) + [layer norm](/llm/knowledge-cards/layer-normalization/) + 換 activation（ReLU / GELU / SwiGLU） |

數學直覺（簡化）：

```text
深 N 層的 chain rule：
∂loss/∂W_input = ∂loss/∂out × ∂out/∂h_N × ∂h_N/∂h_{N-1} × ... × ∂h_1/∂W_input
                                └──────────── N 個 factor 連乘 ──────────────┘

若每個 factor ≈ 0.5、N=100：累乘 ≈ 0.5^100 ≈ 0       → vanishing
若每個 factor ≈ 1.5、N=100：累乘 ≈ 1.5^100 ≈ 4e17    → explosion
```

[Residual connection](/llm/knowledge-cards/residual-connection/) 讓 gradient 有「捷徑」可走、不全靠 chain rule 一層層乘、是深層 Transformer 訓得起來的核心結構之一。

## 設計責任

讀訓練 log 看到 `loss: nan`、`grad_norm: inf` 就是 explosion；看到 loss 平穩、幾個 epoch 都不降就是可能的 vanishing。寫 code 場景幾乎不會碰到（推論不算 gradient）、但自己 fine-tune 時要會判讀。LLM 用的 SwiGLU / GELU 都是 saturation 較不嚴重的 activation、加上 [residual](/llm/knowledge-cards/residual-connection/) + [pre-norm](/llm/knowledge-cards/layer-normalization/)、現代 Transformer 訓 100+ 層相對穩定。
