---
title: "Gradient"
date: 2026-05-12
description: "loss function 對權重的偏微分向量、指出「該往哪個方向調權重才能讓 loss 下降最快」"
weight: 1
tags: ["llm", "knowledge-cards", "training", "math"]
---

Gradient（梯度）的核心概念是「[loss function](/llm/knowledge-cards/loss-function/) 對每個權重的偏微分組成的向量」。每個分量回答「這個權重往正方向動一單位、loss 會變多少」、整個 gradient 向量指向「loss 上升最快的方向」、所以訓練時往**反方向**走、就是讓 loss 下降最快的方向。

## 概念位置

Gradient 連接「loss」跟「該怎麼更新權重」兩件事、是 [backpropagation](/llm/knowledge-cards/backpropagation/) 算出來的東西、也是 SGD / Adam 等 optimizer 消費的輸入：

```text
[forward pass] → 算出 loss
                    ↓
[backpropagation] → 算出 gradient（每個權重一個值）
                    ↓
[optimizer] → 用 gradient 更新權重：w_new = w_old - lr × gradient
```

Gradient 在 LLM 訓練中的兩個常見問題：

| 問題          | 訊號                                    | 處理                                                             |
| ------------- | --------------------------------------- | ---------------------------------------------------------------- |
| Gradient 爆炸 | loss 突然變 NaN、梯度 norm > 1000       | Gradient clipping（截斷 norm 上限）、降 learning rate            |
| Gradient 消失 | 深層權重幾乎不更新、loss 停在某 plateau | Residual connection、Layer normalization、改 activation function |

## 設計責任

推論階段（拿訓練好的模型生 token）**不需要算 gradient**、只有 forward pass；gradient 只在訓練 / fine-tuning 階段出現。所以本地跑 LLM 寫 code 的場景不會碰到 gradient、但讀懂訓練流程、理解「為什麼 SFT / RLHF 需要 GPU、推論不一定要」這類判讀就要先理解 gradient 的角色。
