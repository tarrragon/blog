---
title: "Backpropagation"
date: 2026-05-12
description: "從 output loss 反向遞推、用 chain rule 算出每個權重的 gradient 的演算法"
weight: 1
tags: ["llm", "knowledge-cards", "training", "math"]
---

Backpropagation（反向傳播）的核心概念是「從輸出端的 loss 開始、用 chain rule 一層層往輸入端遞推、算出每個權重的 [gradient](/llm/knowledge-cards/gradient/)」。它是訓練神經網路的核心演算法、沒有它就無法在合理時間內訓練深度模型。

## 概念位置

Backpropagation 是訓練 loop 的中段、夾在 forward pass 跟權重更新之間：

```text
[forward pass]：input → layer1 → layer2 → ... → output → loss
                                                          ↓
[backpropagation]：把 loss 對最後一層權重的偏微分算出來
                  ←─ chain rule ─ 再往前傳播一層、算前一層的 gradient
                  ←─ chain rule ─ ...一路傳回輸入層
                                                          ↓
[optimizer step]：每個權重 w 用對應的 gradient 更新
```

關鍵特性：

1. **計算成本 ≈ forward pass 的 2~3 倍**：每個 layer 都要存 forward 階段的中間值（activation）、反向時拿來算 gradient。所以訓練比推論貴一個量級。
2. **記憶體佔用 = forward 階段 activation 的累計**：這是訓練比推論吃 VRAM 的主因、不是「權重變大」、是「activation 要存著」。
3. **數值穩定性敏感**：long chain 的 chain rule 容易導致 gradient 爆炸或消失、見 [gradient](/llm/knowledge-cards/gradient/) 卡。

## 設計責任

推論階段完全不用 backpropagation。理解這點能解釋幾個現象：為什麼同樣模型訓練要 8 卡 H100 一週、推論單卡就跑得動（差幾十倍的計算與記憶體需求）；為什麼 LoRA / QLoRA 等 parameter-efficient fine-tuning 能大幅降低訓練成本（凍住大部分權重、只對少數 LoRA 矩陣做 backpropagation）；為什麼 inference framework（llama.cpp、vLLM）跟 training framework（PyTorch、JAX）的設計重點完全不同。
