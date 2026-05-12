---
title: "2.2 微積分與最佳化"
date: 2026-05-11
description: "從 gradient、chain rule 到 SGD / Adam：LLM 訓練如何更新數十億參數"
tags: ["llm", "math", "optimization"]
weight: 2
---

LLM 訓練的本質是「最佳化問題」：給定 [loss function](/llm/knowledge-cards/loss-function/)（預訓練用 [cross-entropy](/llm/knowledge-cards/cross-entropy/)、推導見 [2.1 機率與資訊論](/llm/02-math-foundations/probability-and-information/)）、找一組權重讓 loss 最小。微積分提供工具回答「往哪個方向調權重能讓 loss 變小」、最佳化演算法回答「具體怎麼一步一步調」。

寫 code 場景的使用者通常無需親自訓練、但理解這條鏈能解釋「為什麼 fine-tuning 要這麼多 GPU」「為什麼 learning rate 是關鍵 hyperparameter」「為什麼 gradient explosion 是常見問題」。本章整理核心概念、不展開完整推導。

## 本章目標

讀完本章後、你應該能：

1. 解釋 gradient 在訓練中扮演的角色。
2. 看到「learning rate = 1e-4」設定時、知道它控制什麼。
3. 區分 SGD、Adam、AdamW 在訓練 LLM 時的取捨。
4. 看到 gradient explosion / vanishing 報告時、知道發生在哪一層。

## 偏導數與 [gradient](/llm/knowledge-cards/gradient/)：往哪個方向走 loss 變小

偏導數（partial derivative）的核心定義是「對多變數函式中的一個變數微分、其他變數視為常數」。記號 `∂f / ∂xᵢ`。

Gradient（梯度）的核心定義是「所有偏導數打包成的向量」：

```text
∇f = (∂f/∂x₁, ∂f/∂x₂, ..., ∂f/∂xₙ)
```

幾何意義：gradient 指向「函式增加最快的方向」、長度等於該方向的變化率。要讓函式變小、就往 gradient 的反方向走。

LLM 訓練的核心步驟：

1. 把訓練資料丟進模型、跑 forward pass、得到預測。
2. 算 loss（預測跟真實答案的差距）。
3. 對所有權重算 gradient：`∇_W loss`。
4. 更新權重：`W ← W - α · ∇_W loss`（α 是 learning rate）。
5. 回到第 1 步、重複數百萬次。

第 4 步的更新公式就是 gradient descent。整個流程的關鍵在 gradient 怎麼算出來。

## Chain rule：把 gradient 從輸出傳到所有權重

Chain rule（連鎖律）的核心定義是「複合函式的導數等於各層導數的乘積」。一變數情況：

```text
若 z = f(g(x))、則 dz/dx = (df/dg) × (dg/dx)
```

多變數情況推廣到 chain rule 的矩陣形式（Jacobian）。

LLM 有數十億參數、每個參數都要算 gradient。Chain rule 讓「從 loss 倒推每個權重的 gradient」變成可計算的問題：

```text
loss
 ↑ ∂loss/∂output
output (last layer)
 ↑ ∂output/∂layer_N_input × chain rule
layer N
 ↑ ...
layer 1
 ↑ ∂layer_1_input/∂W₁
weights W₁
```

每層算「local gradient」（output 對 input 的導數）、chain rule 把它們乘起來、最終得到 loss 對每個權重的 gradient。這個流程叫 **[backpropagation](/llm/knowledge-cards/backpropagation/)**（反向傳播）。

詳細展開見 [3.0 神經網路基礎](/llm/03-theoretical-foundations/neural-network-basics/)。

## [Learning Rate](/llm/knowledge-cards/learning-rate/)：每步走多遠

Learning rate（學習率）的核心定義是「gradient descent 每步更新的幅度」、記號 α 或 η。權重更新：

```text
W_new = W_old - learning_rate × gradient
```

Learning rate 的影響：

| Learning rate | 效果                                           |
| ------------- | ---------------------------------------------- |
| 太大          | 跨過最佳解、loss 震盪不收斂、甚至發散          |
| 適中          | 穩定下降、合理時間內收斂                       |
| 太小          | 收斂太慢、訓練時間爆增、可能卡在 local minimum |

LLM 訓練常用 learning rate：

- 預訓練（pre-training）：1e-4 ~ 3e-4、有 warmup 後線性衰減
- Fine-tuning：1e-5 ~ 5e-5、較小避免破壞 pre-trained 權重
- LoRA：1e-4 ~ 1e-3、只更新少量參數可較大

Learning rate 是訓練 LLM 最關鍵的 hyperparameter、設錯時整個訓練容易失敗、實務上極難救回。實務上常用 learning rate scheduler 動態調整：warmup + cosine decay 是最主流的組合。

## [SGD](/llm/knowledge-cards/sgd/)：最基本的最佳化演算法

SGD（Stochastic Gradient Descent、隨機梯度下降）的核心定義是「每次只用一小批資料（mini-batch）算 gradient、更新權重」。對應 vanilla gradient descent（用全部資料算一次）的計算成本問題：

- **Batch GD**：每步用全部訓練資料、gradient 準但每步成本高、適合小資料集
- **SGD（mini-batch）**：每步用 32 ~ 256 筆、gradient 有 noise 但平均下來方向對、適合大資料集

LLM 預訓練資料動輒 TB 級、每步只能用 mini-batch；每個 token 算一次 forward + backward、跑數兆 token、總更新數十萬到數百萬步。

Vanilla SGD 在 LLM 場景的缺點：

1. 對 learning rate 敏感、不同 layer / 不同參數可能需要不同 learning rate。
2. 在「狹長 loss surface」上震盪、收斂慢。
3. 不利用過去 gradient 資訊。

SGD-with-momentum 在 vanilla SGD 上補了「過去 gradient 累積成 velocity」、處理震盪問題、在 vision（ResNet、ImageNet 訓練）跟小規模 fine-tune 仍是合理選擇；Adam / AdamW 在 LLM 預訓練成主流的原因是「自適應 learning rate + per-parameter scale」更能對付 Transformer 的高維、稀疏 gradient 結構、大規模 transformer 預訓練幾乎全部用 AdamW。

## [Adam 與 AdamW](/llm/knowledge-cards/adam-adamw/)：適應性最佳化

Adam（Adaptive Moment Estimation）的核心定義是「每個參數有自己的有效 learning rate、根據過去 gradient 的一階矩跟二階矩自動調整」。簡化版本：

```text
m_t = β₁ × m_{t-1} + (1 - β₁) × gradient   ← 一階矩（gradient 的指數移動平均）
v_t = β₂ × v_{t-1} + (1 - β₂) × gradient²  ← 二階矩（gradient 平方的指數移動平均）
update = learning_rate × m_t / (sqrt(v_t) + ε)
```

直覺：

- 一階矩 m：類似動量、讓更新方向有慣性、減少震盪。
- 二階矩 v：估計 gradient 大小、把更新除以 sqrt(v)、自動調整每個參數的有效步幅。
- 結果：高 gradient 的參數步小、低 gradient 的參數步大、整體穩定收斂。

AdamW 是 Adam 的改進版、把 weight decay（L2 正則化）跟 gradient update 解耦。大規模 transformer 預訓練幾乎都用 AdamW、vanilla Adam 已退出 LLM 主流（SGD-with-momentum 在 vision 跟小規模 fine-tune 仍適用）。

代價：Adam / AdamW 需要為每個參數額外存 m（一階矩、gradient 的指數移動平均）跟 v（二階矩、gradient 平方的指數移動平均）、記憶體成本是 SGD 的 3 倍。31B 模型用 AdamW 訓練的 optimizer state 約佔 200GB+ 記憶體、拆解如下（mixed-precision training、batch=1024 / 不含 activation checkpoint 的典型配置）：

- fp32 master weights：31B × 4 bytes ≈ 124 GB
- m（一階矩）：31B × 4 bytes ≈ 124 GB
- v（二階矩）：31B × 4 bytes ≈ 124 GB
- 總計約 372 GB optimizer state、加上 activation 與 gradient buffer 後實際需求更高

對比推論時 Gemma 4 31B Q4 量化版約 18GB（含 KV cache、見 [0.5 Apple Silicon 記憶體預算](/llm/00-foundations/hardware-memory-budget/)）、訓練需求是推論的 20 倍以上。這就是為什麼訓練 LLM 需要大量 GPU、推論可以在個人 Mac 上跑。

## [Gradient Explosion 與 Vanishing](/llm/knowledge-cards/gradient-explosion-vanishing/)

Gradient explosion（梯度爆炸）的核心問題是「gradient 經過多層 chain rule 累積、變成天文數字、權重更新後完全爆掉」。常見於深度網路、特別是 RNN。

Gradient vanishing（梯度消失）的反面問題是「gradient 經過多層後變得幾乎為 0、深層 layer 學不到東西」。常見於用 sigmoid / tanh activation 的深度網路。

Transformer 為什麼能訓練深層網路：

1. **Residual connection**：跨層加上 `x + f(x)`、給 gradient 一條短路、避免 vanishing。
2. **Layer normalization**：每層 activation 重新正規化、避免數值爆炸。
3. **適當的權重初始化**：Xavier / Kaiming 初始化讓初始 forward pass 不爆。
4. **Gradient clipping**：訓練時把 gradient 的 norm 截斷在閾值內、避免 explosion。

詳細展開見 [3.3 Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)。

## Backpropagation：chain rule 在多層網路上的演算法名

Backpropagation（反向傳播）就是前面 [chain rule](#chain-rule把-gradient-從輸出傳到所有權重) 段講的「∂loss/∂W 倒推流程」在實作上的演算法名稱、不是另一個獨立概念。整體流程：forward pass 算 output 與 loss、backward pass 用 chain rule 從 loss 逐層倒推每個權重的 gradient、framework（PyTorch / MLX）的 autograd 自動完成 backward、開發者只需寫 forward。Autograd 跟 chain rule / backprop 是同個概念在不同抽象層級的展開。

## 為什麼推論不需要 backprop

寫 code 場景用 LLM 是「推論」而非「訓練」。推論只跑 forward pass、不算 gradient、不更新權重。所以：

1. **記憶體需求低得多**：推論不用存中間 activation（forward pass 結束就可丟）、不用存 optimizer state。Gemma 4 31B 推論約 18GB、訓練同個模型可能要 200GB+。
2. **算力需求低得多**：推論一個 token 要 1 次 forward pass、訓練一個 token 要 forward + backward = 約 3 次 forward 的成本。
3. **沒有 learning rate / optimizer 等 hyperparameter**：推論只有 temperature、top-p 等 sampling 參數。

這就是為什麼 32GB Mac 可以推論 31B 模型、訓練同個模型要動用整個 H100 cluster。

## 小結

LLM 訓練是「最小化 loss」的最佳化問題、用 chain rule + backpropagation 算 gradient、用 SGD / AdamW 更新權重。Learning rate 是最關鍵的 hyperparameter、AdamW 的 optimizer state 是訓練記憶體的主要消耗源。寫 code 場景的推論只跑 forward pass、成本只有訓練的零頭。

想看完整最佳化理論（凸最佳化、二階方法、Hessian、Newton's method 等）、見 [2.4 公開課推薦](/llm/02-math-foundations/going-deeper-math/) 的 Stanford EE364 / CS229 等課程。

下一章：[2.3 數值精度與量化的數學依據](/llm/02-math-foundations/numerical-precision/)。
