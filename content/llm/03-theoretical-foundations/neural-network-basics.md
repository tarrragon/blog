---
title: "3.0 神經網路基礎"
date: 2026-05-11
description: "從單一 neuron 到 multi-layer：weights、activation function、forward / backward pass 的角色"
tags: ["llm", "theory", "neural-network"]
weight: 0
---

神經網路（Neural Network、NN）是 LLM 的底層架構。完整描述需要從「單一 neuron 怎麼算」開始、堆疊成 layer、串成 multi-layer network、再加上訓練機制（forward pass 跑預測、backward pass 算 gradient）。本章把這條鏈走過一遍、為後續章節的 embedding、attention、Transformer 架構建立詞彙基底。

本章預設讀者熟悉[線性代數](/llm/02-math-foundations/linear-algebra-for-llm/)（矩陣乘法、向量內積）跟[微積分](/llm/02-math-foundations/calculus-and-optimization/)（gradient、chain rule）。沒讀過模組二的讀者、可以先讀本章看哪些術語陌生再回頭補。

## 本章目標

讀完本章後、你應該能：

1. 解釋「一個 layer 在做什麼」用線性代數的話。
2. 區分 activation function 的常見選擇（ReLU、GELU、SiLU）的差異。
3. 解釋為什麼神經網路需要非線性 activation。
4. 看到「N-layer Transformer」時、能對應到模型結構。

## 單一 neuron：linear + activation

單一 neuron（神經元）的核心定義是「對輸入做線性組合、再經過非線性函式」：

```text
output = activation(w · x + b)
```

其中：

- `x`：輸入向量
- `w`：權重向量
- `b`：bias（純量）
- `w · x`：[內積](/llm/02-math-foundations/linear-algebra-for-llm/)
- `activation`：非線性函式（如 ReLU、sigmoid、tanh）

直覺：先把輸入做加權求和、再用非線性函式扭曲一下。沒有非線性、堆 N 個 neuron 等同於一個線性變換、表達能力有限。

## Layer：把 N 個 neuron 並排

Layer（層）的核心定義是「把多個 neuron 並排處理同一個輸入」、結構上等同於矩陣乘法 + 向量加 bias + 逐元素 activation：

```text
output = activation(W @ x + b)
```

其中：

- `W`：權重矩陣、shape `(output_dim, input_dim)`
- `x`：輸入向量、shape `(input_dim,)`
- `b`：bias 向量、shape `(output_dim,)`
- `W @ x`：[矩陣乘法](/llm/02-math-foundations/linear-algebra-for-llm/)
- 結果 `output`：shape `(output_dim,)`

例：input dim = 4096、output dim = 4096 的 layer、權重矩陣有 16,777,216 個參數。

這種「`activation(W @ x + b)`」結構叫 **linear layer**、**fully-connected layer**、或 **dense layer**、是神經網路最基本的 building block。

## Activation Function：引入非線性

Activation function（激活函式）的核心責任是「在每個 layer 後引入非線性、讓網路能表達複雜函式」。沒有它、N 個線性 layer 等同於一個線性 layer。

主流 activation function：

| 函式         | 公式                            | 特性                                        |
| ------------ | ------------------------------- | ------------------------------------------- |
| ReLU         | max(0, x)                       | 簡單、快、深度網路標準選擇                  |
| GELU         | x × Φ(x)、Φ 是高斯 CDF          | ReLU 的平滑版、Transformer 內 FFN 常用      |
| SiLU / Swish | x × sigmoid(x)                  | 跟 GELU 類似、Llama 系列用                  |
| sigmoid      | 1 / (1 + e^{-x})                | 早期常用、現在多半被 ReLU 系取代            |
| tanh         | (e^x - e^{-x}) / (e^x + e^{-x}) | 早期 RNN 常用、輸出在 -1 到 1 之間          |
| softmax      | exp(xᵢ) / Σⱼ exp(xⱼ)            | 不是逐元素 activation、用在輸出層轉機率分佈 |

Transformer 內部主要用 GELU 或 SiLU。Sigmoid 跟 tanh 在深度 30+ 的網路中容易造成 [gradient vanishing](/llm/02-math-foundations/calculus-and-optimization/)、Transformer 系列因此採用 GELU / SiLU；淺層網路（< 10 層）兩者影響較小、Sigmoid / tanh 仍可用。

[Softmax](/llm/02-math-foundations/probability-and-information/) 是特殊 activation、用在輸出層把 logits 轉成機率分佈、不在中間 layer 用。

## Multi-Layer Network：串接 N 個 layer

Multi-layer network（多層網路）的核心結構是「N 個 layer 串接、前一層的 output 是下一層的 input」：

```text
h₁ = activation₁(W₁ @ x + b₁)
h₂ = activation₂(W₂ @ h₁ + b₂)
...
output = activation_N(W_N @ h_{N-1} + b_N)
```

「深度」（depth）指 layer 數量。Transformer LLM 的 layer 數通常 30 ~ 80：

| 模型          | Layer 數 | Hidden Dim |
| ------------- | -------- | ---------- |
| GPT-2 small   | 12       | 768        |
| Llama 3.3 8B  | 32       | 4096       |
| Llama 3.3 70B | 80       | 8192       |
| Gemma 4 31B   | 約 50    | 約 5120    |

每層都是線性變換 + activation；堆疊起來表達能力強。但深度高也意味著訓練難度高（[gradient vanishing / explosion](/llm/02-math-foundations/calculus-and-optimization/)）、需要 residual connection 跟 layer norm 等技術配合。

## Forward Pass：從 input 算到 output

Forward pass（前向傳播）的核心定義是「資料從 input 流經各層、產生 output 的計算過程」。每個 layer 順序做矩陣乘法 + activation。

LLM 的 forward pass 概略流程：

```text
input tokens → embedding layer → 數十個 Transformer block → output layer → logits
```

每個 Transformer block 內部又包含 attention + feed-forward + 兩個 layer norm。詳細展開見 [3.3 Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)。

寫 code 場景的推論完全是 forward pass、不涉及 backward pass。每生一個 token 跑一次 forward pass、由 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 決定速度上限。

## Backward Pass：從 loss 算 gradient

Backward pass（反向傳播）的核心定義是「用 [chain rule](/llm/02-math-foundations/calculus-and-optimization/)、從 loss 倒推每個權重的 gradient」。它是訓練神經網路的基礎。

流程：

1. **Forward**：input → output → loss。
2. **Backward**：從 loss 開始、逐層算 local gradient、用 chain rule 累積。
3. **Update**：用 gradient 更新權重（[gradient descent](/llm/02-math-foundations/calculus-and-optimization/)）。

實作上、PyTorch / MLX 等 framework 用 autograd 自動算 backward、開發者只寫 forward。

推論時無 backward pass、所以推論的記憶體跟算力需求遠低於訓練。

## Bias：可選的常數項

Bias 的核心定義是「neuron 的 `w · x + b` 中的 `+ b`」、讓 neuron 的輸出可以平移。

在 hidden_dim ≥ 4096 規模下、bias 對品質的邊際貢獻被觀察為近零、近年大型 LLM 普遍取消 bias 參數：

- Llama 系列、Gemma 系列、Qwen 系列都把 bias 設為 0、不訓練 bias 參數。
- 理由：實驗發現此規模下拿掉 bias 對品質影響微小、但能省記憶體與計算。

某些早期 LLM（GPT-2 等）跟舊架構仍用 bias、小規模網路 / 特殊任務下 bias 仍有實際貢獻。看模型 config 可知這個模型是否含 bias 參數。

## Hidden Layer 與 Hidden Dimension

Hidden layer 的核心定義是「介於 input layer 跟 output layer 之間的中間 layer」。Hidden dimension（hidden_dim、d_model）是這些 layer 的輸出向量維度、規格見前一節 [Multi-Layer Network](#multi-layer-network串接-n-個-layer) 的表格。

Hidden dim 是模型「表達能力」的主要維度之一。每個 token 在模型內部都是一個 hidden_dim 維向量、layer 越大越能編碼複雜資訊。

## 為什麼需要這麼多 parameter

LLM 參數量主要來自 layer 數 × 每層權重矩陣大小、其中 FFN 層約佔 2/3。每個 layer 的權重矩陣大小是 `hidden_dim × hidden_dim`（feed-forward layer 通常 `hidden_dim × 4 × hidden_dim`、4 倍的由來見 [3.3 Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)）、加上 attention 的 Q/K/V projection 等、單一 layer 已有上億參數。

Gemma 4 31B 約 50 layer、每層約 600M 參數、合計約 31B。70B / 405B 模型也是類似結構放大。

參數數量越多、模型「能學到的 pattern」越多。預訓練資料 trillion token 級別、需要大模型才能完整「記住」這些 pattern。實務上邊際收益隨參數量遞減（同代架構下參數翻倍、benchmark 提升通常 < 5%）、且推論成本線性增加；這就是為什麼 31B / 70B 級別停滯一段時間後、業界把焦點轉向 [MoE](/llm/knowledge-cards/moe-cpu-offload/) 等「不增加每 token 算量」的擴張路徑。

## 何時這套基礎不適用

本章的「neuron → linear layer → forward / backward pass」假設「純 dense Transformer」架構、實務上有幾類架構走不同的計算路徑、判讀新架構時要對應調整：

| 架構                          | 跟本章基礎的差異                                                                |
| ----------------------------- | ------------------------------------------------------------------------------- |
| MoE（Mixture of Experts）     | 每個 token 只啟用部分專家層、forward pass 中 router 動態決定哪些 dense layer 跑 |
| SSM（如 Mamba）               | 用 state-space 遞迴取代 attention、forward 結構跟「層層 dense」不同             |
| Diffusion 模型                | U-Net 結構含 down-sampling + up-sampling、跟純 stack 的 Transformer 拓撲不同    |
| Recurrent LLM 變體（如 RWKV） | 走 recurrent state、不純做 forward stack                                        |

判讀新架構時、先把它跟本章的 dense Transformer baseline 對照、找出在哪一步岔開（哪個 layer 結構、forward 順序、parameter sharing）、再深入差異點。

## 下一章

下一章：[3.1 embedding 空間](/llm/03-theoretical-foundations/embedding-spaces/)、從「token 怎麼變成向量」開始。
