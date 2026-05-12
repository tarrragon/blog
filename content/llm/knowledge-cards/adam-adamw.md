---
title: "Adam / AdamW"
date: 2026-05-12
description: "對每個參數自適應 learning rate 的 optimizer、LLM 訓練主流選擇"
weight: 1
tags: ["llm", "knowledge-cards", "training", "optimizer"]
---

Adam（Adaptive Moment Estimation、Kingma & Ba, 2014）的核心概念是「**對每個參數維護兩個 EMA**（gradient 的一階矩 = 平均、二階矩 = 變異）、用這兩個值自適應地縮放每個參數的更新步長」。AdamW（Loshchilov & Hutter, 2017）是 Adam 加上「decoupled weight decay」的修正版、是現代 LLM 訓練的標準 optimizer。

## 概念位置

Adam 更新規則（簡化）：

```text
m_t = β₁ × m_{t-1} + (1 - β₁) × g_t      ← gradient 的 EMA（一階矩、方向）
v_t = β₂ × v_{t-1} + (1 - β₂) × g_t²     ← gradient² 的 EMA（二階矩、變動率）
W -= lr × m_t / (sqrt(v_t) + ε)
            └──────┬──────┘
        每個參數獨立縮放
        經常變動的方向減小步長、穩定方向加大
```

跟其他 optimizer 對比：

| 對比           | [SGD](/llm/knowledge-cards/sgd/) | SGD + Momentum | Adam        | AdamW                      |
| -------------- | -------------------------------- | -------------- | ----------- | -------------------------- |
| 每參數自適應   | 否                               | 否             | 是          | 是                         |
| 記憶體開銷     | 1× W（就 gradient）              | 2× W           | 3× W        | 3× W                       |
| Hyperparameter | lr                               | lr + μ         | lr + β₁、β₂ | lr + β₁、β₂ + weight_decay |
| LLM 訓練主流   | 否                               | 否             | 早期        | 現在主流                   |

關鍵：AdamW 對 weight decay 跟 lr 解耦、修正了 Adam 在「lr × weight_decay」交互上的 bug、是 GPT、Llama、Gemma 等系列訓練的標配。

## 設計責任

讀 LLM training paper / config 看到 `optimizer: AdamW`、`betas: [0.9, 0.95]`、`weight_decay: 0.1` 等就是這個 optimizer 的標準設定。記憶體佔用 = 模型權重 × 3（model + m + v）、加上 [backpropagation](/llm/knowledge-cards/backpropagation/) 的 activation、是訓練 vs 推論記憶體差距的主要來源。
