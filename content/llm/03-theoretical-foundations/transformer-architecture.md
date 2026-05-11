---
title: "3.3 Transformer 架構細節"
date: 2026-05-11
description: "Decoder-only 結構、Transformer block、positional encoding、layer norm、residual stream"
tags: ["llm", "theory", "transformer"]
weight: 3
---

Transformer 把 [embedding](/llm/03-theoretical-foundations/embedding-spaces/) 與 [attention](/llm/03-theoretical-foundations/attention-mechanism/) 組合成完整 forward pass 結構。LLM 用的是「decoder-only Transformer」、跟原始 paper（Vaswani et al., 2017）的 encoder-decoder 結構不同。本章把現代 LLM（Llama / Gemma / Qwen 系列）的 Transformer 架構走過一遍、解釋每個組件的角色。

理解整個架構後、看 LLM paper 中的「residual stream」「pre-norm vs post-norm」「FFN」「MoE」等術語都能對到具體位置。

## 本章目標

讀完本章後、你應該能：

1. 畫出一個 Transformer block 的結構。
2. 解釋 positional encoding 的角色與選擇。
3. 看到 RMSNorm、SwiGLU 等術語時、知道是 layer norm / activation 的變體。
4. 解釋為什麼現代 LLM 普遍用 decoder-only 架構。

## Encoder vs Decoder：兩種 Transformer

原始 Transformer paper 提出 encoder-decoder 結構、用於機器翻譯：

- **Encoder**：處理 input sequence、產生 contextual embedding。雙向 attention（每個 token 可看所有 token）。
- **Decoder**：根據 encoder 輸出 + 已生成 tokens、產生下一個 token。Causal attention（只看前面）。

後續發展出三種主流變體：

| 類型            | 例子              | 適合任務                  |
| --------------- | ----------------- | ------------------------- |
| Encoder-only    | BERT、RoBERTa     | 分類、實體識別、retrieval |
| Decoder-only    | GPT、Llama、Gemma | 生成、對話、寫 code       |
| Encoder-Decoder | T5、BART          | 翻譯、摘要、seq-to-seq    |

寫 code 場景接觸到的所有主流 LLM（GPT、Claude、Gemma、Llama、Qwen）都是 **decoder-only**、只用 causal attention、用「文字接龍」方式做所有任務（chat、寫 code、翻譯都統一成「給前面文字、生成後面文字」）。

本章其他部分聚焦 decoder-only 結構。

## 整體 forward pass

Decoder-only Transformer 的 forward pass：

```text
input tokens [t1, t2, ..., tn]
  ↓ embedding lookup
embeddings [e1, e2, ..., en]   (shape: seq_len × hidden_dim)
  ↓ + positional encoding（如 RoPE）
positioned embeddings
  ↓ Transformer block 1
  ↓ Transformer block 2
  ↓ ...
  ↓ Transformer block N（30 ~ 80 層）
final hidden states
  ↓ final layer norm
normalized states
  ↓ output projection
logits [vocab_size]
  ↓ softmax
下個 token 的機率分佈
```

每個 Transformer block 內部結構（後面展開）。

## Transformer Block：架構核心

一個 Transformer block 包含兩個 sub-layer、各自前後加 layer norm 跟 residual connection。現代 LLM 用的「pre-norm」結構：

```text
input x
  ↓
norm 1 (RMSNorm)
  ↓
multi-head attention（causal）
  ↓
+ x（residual connection）
  ↓
中間結果 y
  ↓
norm 2 (RMSNorm)
  ↓
FFN（feed-forward network）
  ↓
+ y（residual connection）
  ↓
output
```

兩個關鍵組件：

1. **Multi-head attention**：見 [3.2](/llm/03-theoretical-foundations/attention-mechanism/)。
2. **FFN**（feed-forward network）：兩層 [linear layer](/llm/03-theoretical-foundations/neural-network-basics/) + 非線性 activation。

每個 sub-layer 前後加 **residual connection**：把 sub-layer 的輸出加回 input、形成「主流」。這個結構讓 gradient 容易在深層網路中傳遞、解決 [gradient vanishing](/llm/02-math-foundations/calculus-and-optimization/) 問題。

## Feed-Forward Network（FFN）

FFN 是 Transformer block 中的第二個 sub-layer、結構是「升維 → activation → 降維」：

```text
FFN(x) = activation(x @ W1) @ W2
```

其中：

- `W1` shape: `(hidden_dim, intermediate_dim)`
- `W2` shape: `(intermediate_dim, hidden_dim)`
- `intermediate_dim` 通常是 hidden_dim 的 2.5 ~ 4 倍

例：Llama 3 8B、hidden_dim 4096、intermediate_dim 14336（約 3.5x）。FFN 是模型大部分參數的來源（attention 的 W_Q/K/V 只佔少數）。

Activation 選擇：

| 模型       | FFN Activation |
| ---------- | -------------- |
| GPT-2      | GELU           |
| Llama 系列 | SwiGLU         |
| Gemma 系列 | GeGLU          |
| Qwen3 系列 | SwiGLU         |

SwiGLU / GeGLU 是 gated 變體、用兩個 linear projection、其中一個過 activation 當 gate：

```text
SwiGLU(x) = (x @ W1) ⊙ SiLU(x @ W3) @ W2
```

⊙ 是逐元素乘法。實驗發現比純 GELU 略好、是現代 LLM 主流。

## Layer Normalization：穩定訓練

Layer normalization（layer norm）的核心定義是「把每個 token 的 hidden vector 重新正規化到 mean=0、variance=1、再用 learnable scale / shift 調整」：

```text
LayerNorm(x) = γ ⊙ (x - mean(x)) / sqrt(var(x) + ε) + β
```

其中 γ、β 是 learnable 參數。

LLM 用的變體：

| 變體      | 機制                             | 用在                      |
| --------- | -------------------------------- | ------------------------- |
| LayerNorm | mean + variance 都正規化         | GPT-2                     |
| RMSNorm   | 只用 root-mean-square、不算 mean | Llama / Gemma / Qwen 系列 |

RMSNorm 比標準 LayerNorm 簡單、計算稍快、品質接近、現代 LLM 主流。

## Pre-Norm vs Post-Norm

Layer norm 的位置有兩個選擇：

- **Post-norm**（原始 Transformer paper）：先做 attention / FFN、再加 residual、再 layer norm。深層網路訓練不穩。
- **Pre-norm**（現代 LLM 主流）：先 layer norm、再做 attention / FFN、再加 residual。訓練穩定、深層網路才能訓得起來。

幾乎所有現代 LLM（Llama / Gemma / Qwen / GPT-3+）都用 pre-norm。

## Residual Connection（殘差連接）

Residual connection 的核心定義是「sub-layer 的輸出加回它的 input」：`output = sublayer(x) + x`。這個結構由 ResNet（He et al., 2015）首先廣泛採用、Transformer 跟現代深度網路都用。

效果：

1. **Gradient 直接傳遞**：backward pass 中 gradient 可直接從深層流回淺層、避免 vanishing。
2. **Identity 是 default**：若 sub-layer 學壞、residual 確保至少不退步（output = x）。
3. **Residual stream 概念**：模型內部可視為一個「主流」、每層 sub-layer 對它做 incremental update。這個視角是現代可解釋性研究（mechanistic interpretability）的核心。

## Positional Encoding：把順序加進去

[Embedding](/llm/03-theoretical-foundations/embedding-spaces/) 章節提到 attention 機制本身沒有順序資訊。Positional encoding 把位置資訊注入、讓 `[cat, dog]` 跟 `[dog, cat]` 有區別。主流方法：

### Sinusoidal（原始 Transformer）

用 sin / cos 不同頻率生成位置向量、加進 token embedding：

```text
PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```

固定值、不訓練。早期 GPT 用、後續被學習式取代。

### Learned Positional Embedding

訓練一個 `(max_seq_len, hidden_dim)` 的矩陣、每個位置一個 embedding、加進 token embedding。GPT-2 用、簡單但有 max_seq_len 限制。

### Rotary Position Embedding（RoPE）

RoPE（Su et al., 2021）的核心想法是「不加位置 embedding、而是把 Q 跟 K 在每個 attention head 內做位置相關的旋轉」：

```text
RoPE(Q, position) = 把 Q 的 2D 子空間按 position 旋轉特定角度
```

優點：

- **相對位置**：attention 看的是兩個 token 的相對距離、不是絕對位置。
- **無 max_seq_len**：理論上可外推到任意長度（實務上有 degradation）。
- **可訓練 + 不需要額外參數**：旋轉角度固定、不增加模型參數。

Llama 系列、Gemma 系列、Qwen 系列都用 RoPE、目前主流。

### ALiBi（Attention with Linear Biases）

ALiBi 的核心想法是「在 attention scores 加一個位置 bias、距離越遠 bias 越負」、attention 自然傾向關注近處。MosaicML 的 MPT 系列用、長 context 外推性質佳。

## 長 Context 的擴展技巧

LLM 在訓練長度（如 8K）以外的 context 上品質會 degradation。擴展長 context 的方法：

| 方法                   | 機制                                         |
| ---------------------- | -------------------------------------------- |
| RoPE scaling           | 把 RoPE 的旋轉頻率縮小、attention 看「更遠」 |
| YaRN                   | RoPE scaling 的改進、保留近距精度            |
| NTK-aware scaling      | 另一種 RoPE 頻率調整方法                     |
| Position interpolation | 把位置 ID 縮放到訓練範圍內                   |

主流 LLM 在預訓練後做這些 scaling、把 context window 從 8K / 32K 擴展到 128K / 1M。代價是長 context 上的精度逐步下降、實用上界 < 聲稱上界。

詳見 [context window](/llm/knowledge-cards/context-window/) 卡片。

## Output Projection：從 hidden 到 logits

Forward pass 最後一步是把最終 hidden states 投射到 vocab size、得到 logits：

```text
logits = final_hidden_states @ W_output
```

`W_output` shape: `(hidden_dim, vocab_size)`。

Gemma 4 31B 的 output projection 參數約 1.3B（hidden 5120 × vocab 262,144）、跟 input embedding 同量級。如果 tied（共用權重）就只算一次；現代 LLM 多半 untied、兩者獨立。

Output 後接 [softmax](/llm/02-math-foundations/probability-and-information/) 轉成下個 token 的機率分佈、進入 [sampling](/llm/03-theoretical-foundations/sampling-and-decoding/) 流程。

## Mixture of Experts（MoE）

Mixture of Experts 是 FFN 的擴展、把單個 FFN 換成 N 個 expert、每個 token 只 route 到 K 個 expert（K << N）。例如 Mixtral 8x7B：

- 每層有 8 個 expert FFN。
- 每個 token 由 router 選 2 個 expert 處理。
- 總參數約 47B、但每個 token 只啟動 12B 左右。

優點：總參數可超大、推論時實際算力只用一小部分。缺點：記憶體仍要載入全部 expert、訓練更複雜。

DeepSeek-V3、Qwen2-MoE、Mixtral 等是知名 MoE 模型。寫 code 場景的 Apple Silicon Mac 暫時較少用 MoE（記憶體預算對 MoE 不友善）。

## 為什麼 LLM 是 decoder-only

現代 LLM 普遍用 decoder-only 架構、背後有幾個理由：

1. **任務統一性**：「文字接龍」框架可以包進對話、寫 code、翻譯、摘要等所有任務。
2. **訓練效率**：causal mask 讓所有位置可以並行訓練（每個 token 都當訓練目標）。
3. **In-context learning**：decoder-only 在 few-shot prompting 上特別強。

GPT-3 證明這套之後、整個產業靠攏 decoder-only。Encoder-decoder（T5 系列）仍有研究價值、但商業 LLM 主流都是 decoder-only。

## 小結

Transformer 是 LLM 的核心架構。Decoder-only 結構由「embedding + positional encoding + N 個 Transformer block + output projection」組成。每個 block 包含 attention sub-layer 跟 FFN sub-layer、各自前後加 RMSNorm 跟 residual connection。現代 LLM 常用 RoPE 位置編碼、SwiGLU FFN、GQA attention、RMSNorm。理解這個結構、看 LLM paper 跟 model architecture 比較就有完整地圖。

下一章：[3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)、解釋這些權重怎麼學出來。
