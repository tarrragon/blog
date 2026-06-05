---
title: "3.3 Transformer 架構細節"
date: 2026-05-11
description: "Decoder-only 結構、Transformer block、positional encoding、layer norm、residual stream"
tags: ["llm", "theory", "transformer"]
weight: 3
---

[Transformer](/llm/knowledge-cards/transformer/) 把 [embedding](/llm/03-theoretical-foundations/embedding-spaces/) 與 [attention](/llm/knowledge-cards/attention/) 組合成完整 forward pass 結構。LLM 用的是「decoder-only Transformer」、跟原始 paper（Vaswani et al., 2017）的 encoder-decoder 結構不同。本章把現代 LLM（Llama / Gemma / Qwen 系列）的 Transformer 架構走過一遍、解釋每個組件的角色。

理解整個架構後、看 LLM paper 中的「residual stream」「pre-norm vs post-norm」「FFN」「MoE」等術語都能對到具體位置。

## 本章目標

讀完本章後、你應該能：

1. 畫出一個 Transformer block 的結構。
2. 解釋 [positional encoding](/llm/knowledge-cards/positional-encoding/) 的角色與選擇。
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

1. **Multi-head attention**：見 [3.2](/llm/03-theoretical-foundations/attention-mechanism/)、Q/K/V 來源同 sequence 的部分見 [self-attention](/llm/knowledge-cards/self-attention/) 卡。
2. **[FFN](/llm/knowledge-cards/ffn/)**（feed-forward network）：兩層 [linear layer](/llm/03-theoretical-foundations/neural-network-basics/) + 非線性 [activation](/llm/knowledge-cards/activation-function/)。

每個 sub-layer 前後加 **[residual connection](/llm/knowledge-cards/residual-connection/)**：把 sub-layer 的輸出加回 input、形成「主流」。這個結構讓 [gradient](/llm/knowledge-cards/gradient/) 容易在深層網路中傳遞、解決 [gradient vanishing](/llm/02-math-foundations/calculus-and-optimization/) 問題。

## Feed-Forward Network（FFN）

> 符號 legend：以下公式中 `@` 表矩陣乘法、`⊙` 表逐元素乘（Hadamard product）、`x` 是 hidden vector。

FFN 是 Transformer block 中的第二個 sub-layer、結構是「升維 → activation → 降維」：

```text
FFN(x) = activation(x @ W1) @ W2
```

其中：

- `W1` shape: `(hidden_dim, intermediate_dim)`
- `W2` shape: `(intermediate_dim, hidden_dim)`
- `intermediate_dim` 通常是 hidden_dim 的 2.5 ~ 4 倍

例：Llama 3 8B、hidden_dim 4096、intermediate_dim 14336（約 3.5x）。FFN 是模型大部分參數的來源（attention 的 W_Q/K/V 只佔少數）。

`intermediate_dim` 比例的邊界：低於 2.5x 時 FFN 的「升維 → 過 activation → 降維」表達能力不足、模型 capacity 跟訓練資料 fit 變差；高於 4x 時邊際參數收益遞減、且推論成本線性增加、不划算。SwiGLU / GeGLU 因為內部有兩個 projection、實作上 `intermediate_dim` 會略低（約 2/3）抵消多出來的參數量。

Activation 選擇：

| 模型       | FFN Activation |
| ---------- | -------------- |
| GPT-2      | GELU           |
| Llama 系列 | SwiGLU         |
| Gemma 系列 | GeGLU          |
| Qwen3 系列 | SwiGLU         |

SwiGLU / GeGLU 屬於 **gated linear unit (GLU) 家族**、用兩個 linear projection、其中一個過 activation 當 gate：

```text
SwiGLU(x) = (x @ W1) ⊙ SiLU(x @ W3) @ W2
```

`SiLU(x) = x × sigmoid(x)`（Swish 的別名）、產出「平滑版的 ReLU」。實驗發現 GLU 家族比純 GELU 略好、是現代 LLM 主流。

## Layer Normalization：穩定訓練

[Layer normalization](/llm/knowledge-cards/layer-normalization/)（layer norm）的核心定義是「把每個 token 的 hidden vector 重新正規化到 mean=0、variance=1、再用 learnable scale / shift 調整」：

```text
LayerNorm(x) = γ ⊙ (x - mean(x)) / sqrt(var(x) + ε) + β
```

其中 γ、β 是 learnable 參數。

LLM 用的變體：

| 變體                                                 | 機制                             | 用在                      |
| ---------------------------------------------------- | -------------------------------- | ------------------------- |
| LayerNorm                                            | mean + variance 都正規化         | GPT-2                     |
| [RMSNorm](/llm/knowledge-cards/layer-normalization/) | 只用 root-mean-square、不算 mean | Llama / Gemma / Qwen 系列 |

RMSNorm 比標準 LayerNorm 簡單、計算稍快、品質接近、在大型 LLM（>7B）上是主流；小模型 / 訓練不穩定需要強正規化的場景下、LayerNorm 仍有實際貢獻。

## Pre-Norm vs Post-Norm

Layer norm 的位置有兩個選擇：

- **Post-norm**（原始 Transformer paper）：先做 attention / FFN、再加 residual、再 layer norm。深層網路訓練不穩、但搭配特殊 init / warmup / 較淺層數（< 12 層）仍可用、encoder-only 模型（BERT）跟特定 transformer variant 仍走這條。
- **Pre-norm**（現代 LLM 主流）：先 layer norm、再做 attention / FFN、再加 residual。訓練穩定、深層網路才能訓得起來。

大型現代 LLM（Llama / Gemma / Qwen / GPT-3+）幾乎都用 pre-norm。Post-norm 在淺層 encoder 或需要 strict bottleneck 的場景仍有實際用途。

## Residual Connection（殘差連接）

[Residual connection](/llm/knowledge-cards/residual-connection/) 的核心定義是「sub-layer 的輸出加回它的 input」：`output = sublayer(x) + x`。這個結構由 ResNet（He et al., 2015）首先廣泛採用、Transformer 跟現代深度網路都用。跨層持續傳遞的 hidden state 主通道見 [residual stream](/llm/knowledge-cards/residual-stream/)。

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

[RoPE](/llm/knowledge-cards/rope/)（Su et al., 2021）的核心想法是「不加位置 embedding、而是把 Q 跟 K 在每個 attention head 內做位置相關的旋轉」：

```text
RoPE(Q, position) = 把 Q 的 2D 子空間按 position 旋轉特定角度
```

旋轉的直覺：兩個 token 在 RoPE 旋轉後做內積、結果只跟「兩者的位置差」相關、跟「絕對位置」無關。所以 RoPE 的內積天然編碼相對位置、attention 看到的是「token i 跟 token j 相隔多遠」、不是「token i 在第 N 個位置」。

優點：

- **相對位置**：attention 看的是兩個 token 的相對距離、不是絕對位置。
- **無 max_seq_len**：理論上可外推到任意長度（實務 degradation：超過訓練長度 4x 後品質明顯下降、超過 8x 後幾乎無用、要搭配 RoPE scaling / YaRN 等技巧）。
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

[Forward pass](/llm/knowledge-cards/forward-pass/) 最後一步是把最終 hidden states 投射到 vocab size、得到 [logits](/llm/knowledge-cards/logit/)：

```text
logits = final_hidden_states @ W_output
```

`W_output` shape: `(hidden_dim, vocab_size)`。

Gemma 4 31B 的 output projection 參數約 1.3B（hidden 5120 × vocab 256,000）、跟 input embedding 同量級。如果 tied（共用權重）就只算一次；現代 LLM 多半 untied、兩者獨立。

Output 後接 [softmax](/llm/knowledge-cards/softmax/) 轉成下個 token 的機率分佈、進入 [sampling](/llm/03-theoretical-foundations/sampling-and-decoding/) 流程。

## Mixture of Experts（MoE）

[Mixture of Experts](/llm/knowledge-cards/moe/) 是 FFN 的擴展、把單個 FFN 換成 N 個 expert、每個 token 只 route 到 K 個 expert（K << N）。例如 Mixtral 8x7B：

- 每層有 8 個 expert FFN。
- 每個 token 由 router 選 2 個 expert 處理。
- 總參數約 47B、但每個 token 只啟動 12B 左右。

優點：總參數可超大、推論時實際算力只用一小部分。缺點：記憶體仍要載入全部 expert、訓練更複雜。

DeepSeek-V3、Qwen2-MoE、Mixtral 等是知名 MoE 模型。寫 code 場景的 Apple Silicon Mac 上 MoE 較少當主力、原因是「總參數要塞進統一記憶體（容量壓力大）」但「速度受限的是啟用權重的頻寬（速度反而可能還好）」、容量 vs 頻寬的 trade-off 跟 dense 模型不同。PC 獨立 GPU 場景可以走 CPU 卸載專家層的路徑、見 [MoE CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/)。

MoE 的常見失敗模式：

- **Router collapse**：訓練時所有 token 都 route 到同幾個 expert、其他 expert 完全沒學到東西。修法是加 auxiliary loss 鼓勵 load balancing。
- **Load imbalance**：推論時某些 expert 太熱門、batch 內排隊；某些 expert 閒置浪費。Production deployment 要監控 per-expert utilization。
- **Memory 壓力高於 dense**：總參數塞滿記憶體、但推論時實際算量只用其中一部分、容量利用率低。記憶體預算吃緊時 dense 模型反而較合適。

## 為什麼 LLM 是 decoder-only

現代 LLM 普遍用 decoder-only 架構、背後有幾個理由：

1. **任務統一性**：「文字接龍」框架可以包進對話、寫 code、翻譯、摘要等所有任務。
2. **訓練效率**：causal mask 讓所有位置可以並行訓練（每個 token 都當訓練目標）。
3. **In-context learning**：decoder-only 在 few-shot prompting 上特別強。

GPT-3 證明這套之後、整個產業靠攏 decoder-only。Encoder-decoder（T5 系列）仍有研究價值、但商業 LLM 主流都是 decoder-only。

## 下一章

下一章：[3.4 訓練流程](/llm/03-theoretical-foundations/training-pipeline/)、解釋這些權重怎麼學出來。
