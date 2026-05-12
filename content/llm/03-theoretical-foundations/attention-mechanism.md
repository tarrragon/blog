---
title: "3.2 Attention 機制"
date: 2026-05-11
description: "Query / Key / Value、scaled dot-product attention、multi-head attention：Transformer 的核心運算"
tags: ["llm", "theory", "attention"]
weight: 2
---

Attention（注意力）是 Transformer 的核心創新、也是 LLM 能處理長 context 的關鍵。它的核心想法是「每個 token 決定該關注前面哪幾個 token」、用 [embedding](/llm/03-theoretical-foundations/embedding-spaces/) 之間的[內積](/llm/02-math-foundations/linear-algebra-for-llm/) 量化「相關性」。理解 attention 後、Multi-head、KV cache、Flash Attention、attention sink 等術語都能放到正確位置。

本章從「為什麼需要 attention」開始、拆 scaled dot-product attention 公式、再展開 multi-head attention 跟 causal masking、最後接到 KV cache 與長 context 場景。

## 本章目標

讀完本章後、你應該能：

1. 用 Q / K / V 三個角色解釋 attention 在算什麼。
2. 看到 attention 公式時、能解讀每個運算的角色。
3. 解釋 multi-head attention 跟 single-head 的取捨。
4. 把 [KV cache](/llm/knowledge-cards/kv-cache/) 跟 attention 公式對上。

## 為什麼需要 attention

LLM 處理「下一個 token 該是什麼」、需要綜合 prompt 中前面所有 token 的資訊。早期解法（RNN、LSTM）用「序列狀態」串接、每個 token 只看到上一步的 hidden state。缺點：

1. **長距離依賴難**：訊息傳遞要跑過所有中間 token、容易遺失。
2. **無法並行**：每步依賴上一步、訓練速度有瓶頸。

Attention 的核心突破是「每個 token 直接看所有前面的 token、無需透過中間 hidden state 傳遞」。每個 token 用 attention scores 決定「該關注哪些前面 token」、用這些 token 的向量加權求和、形成自己的 context-aware 表示。

Attention 帶來三個性質：兩個是優勢、一個是代價：

- **優勢一、長距離依賴變直接**：attention 直接連到任何位置、不再需要透過 RNN 的中間 hidden state 接力。
- **優勢二、可以並行**：不同 token 的 attention 計算彼此獨立、訓練時整段序列一次跑完。
- **代價、O(n²) 計算複雜度**：seq_len = n 時要算 n × n 個 attention scores、長 context 場景成本暴增、見後面的 KV cache 與 Flash Attention 段。

## Q / K / V 三個角色

Attention 給每個 token 三個向量、各自有不同角色：

| 角色      | 直覺                         | 數學        |
| --------- | ---------------------------- | ----------- |
| Query (Q) | 「我在找什麼」               | Q = X @ W_Q |
| Key (K)   | 「我有什麼可以被找到」       | K = X @ W_K |
| Value (V) | 「找到我之後、要傳出去什麼」 | V = X @ W_V |

其中 X 是 input embedding、`W_Q`、`W_K`、`W_V` 是三個 learnable 權重矩陣。

直覺：

- 每個 token 同時當「找東西的人」（query）跟「被找的東西」（key + value）。
- Query 跟其他 token 的 Key 內積、得到「該關注每個 token 多少」的分數。
- 用這些分數對所有 token 的 Value 加權求和、得到當前 token 的 context-aware 表示。

## Scaled Dot-Product Attention：核心公式

Attention（Vaswani et al., 2017）的核心公式：

```text
Attention(Q, K, V) = softmax(Q @ K^T / sqrt(d_k)) @ V
```

逐步拆解：

1. **`Q @ K^T`**：所有 query 跟所有 key 兩兩內積、得到 `(seq_len, seq_len)` 矩陣。矩陣 [i][j] 等於「token i 該關注 token j 多少」的原始分數。
2. **`/ sqrt(d_k)`**：scale by sqrt of key dimension。若沒有這步、d_k 大時 softmax 會極端化、訓練不穩。
3. **`softmax(...)`**：對每一 row 做 [softmax](/llm/02-math-foundations/probability-and-information/)、把分數正規化成機率分佈、保證「每個 token 對所有前面 token 的注意力總和 = 1」。
4. **`@ V`**：用 attention 機率對所有 token 的 V 加權求和、得到 `(seq_len, d_v)` 的輸出。每個輸出 row 是該 token 整合了前面所有 token 資訊的 context-aware 表示。

這個公式叫 **scaled dot-product attention**、是 Transformer 的核心運算。

## Multi-Head Attention：多個 attention 並行

Multi-head attention 的核心想法是「跑 N 個獨立的 attention、每個 head 各自有自己的 W_Q / W_K / W_V、結果 concatenate 再過一個線性層」：

```text
head_i = Attention(Q W_Q_i, K W_K_i, V W_V_i)
MultiHead(Q, K, V) = Concat(head_1, ..., head_h) @ W_O
```

幾何意義：每個 head 學「關注一種 pattern」。例如：

- Head 1 可能學到「關注名詞的修飾語」。
- Head 2 可能學到「關注前後標點」。
- Head 3 可能學到「關注 quotation 邊界」。

實驗發現不同 head 確實學到可解釋的功能（雖然多數 head 的功能難以直觀標籤）。在主流規模（hidden_dim ≥ 768、num_heads ≥ 8）下、multi-head 比 single-head 表達能力強；極小模型（hidden_dim < 256）下 multi-head 收益遞減、有時 single-head 更穩定。

主流 LLM 的 head 數：

| 模型        | num_heads | head_dim | hidden_dim |
| ----------- | --------- | -------- | ---------- |
| GPT-2 small | 12        | 64       | 768        |
| Llama 3 8B  | 32        | 128      | 4096       |
| Llama 3 70B | 64        | 128      | 8192       |
| Gemma 4 31B | 約 40     | 約 128   | 約 5120    |

關係：`hidden_dim = num_heads × head_dim`。每個 head 處理 head_dim 維、parallel 跑完再 concatenate 回 hidden_dim。

## Causal Mask：只看前面、不看後面

LLM 是 [autoregressive](/llm/knowledge-cards/autoregressive/)、生成 token N 時只能看 token 0 到 N-1、不能看後面（後面還沒生）。Attention 機制要「擋掉未來位置」、用 **causal mask** 實現：

```text
masked_scores[i][j] = scores[i][j]   if j ≤ i
                    = -∞              if j > i
```

把未來位置的 attention score 設為 -∞、softmax 後機率為 0、等於完全忽略未來。

實作上 mask 是一個下三角矩陣、訓練跟推論時都套用、但角色不同：

- **訓練時的 causal mask**：讓 decoder 能「一次 forward pass 算所有 N 個 token 的 loss」、parallel 訓練。沒有 mask 就要對每個位置跑 N 次 forward（位置 i 只給 token 0 ~ i-1）、訓練速度掉一個量級。這是 Transformer 取代 RNN 在訓練效率上的關鍵。
- **推論時的 causal mask**：每生新 token 只看前面已生的 token、不能 peek 未來。實際因為 token 是按順序生成的、未來位置本來就還沒存在、mask 更像是「沿用訓練階段的同套運算結構、避免訓練 / 推論 mismatch」。

「Decoder-only LLM」（GPT、Llama 系列）用 causal mask 做自回歸生成；「Encoder-only LLM」（BERT 等）不用 causal mask、可看雙向 context、適合分類 / NER 等理解任務、不走自回歸生成路徑；「Encoder-Decoder」（T5、BART）encoder 看雙向、decoder 用 causal mask、可生成、是另一條典型架構。

## KV Cache：避免重複計算

[KV Cache](/llm/knowledge-cards/kv-cache/) 是 attention 機制下的關鍵優化。回到 attention 公式：

```text
Attention(Q, K, V) = softmax(Q @ K^T / sqrt(d_k)) @ V
```

生成 token N 時：

- Q 是 token N 對應的 query（新的）。
- K、V 是 token 0 到 N-1 的 key / value（前面都算過）。

如果每生一個 token 都重新算 K、V、會浪費大量計算。KV cache 把 K、V 存起來、下次生 token N+1 時：

- Q 是 token N+1 的新 query。
- K、V 是 cache + 新 token 的 K、V。

只算 token N+1 對應的 K、V 新值、跟既有 cache concat。每生一個 token 的計算量從 O(n²) 降到 O(n)。

代價是 KV cache 隨 [context window](/llm/knowledge-cards/context-window/) 線性增長、長 context 場景吃記憶體。Gemma 4 31B 在 32GB Mac 上實用 context 約 8 ~ 16K tokens、超過會 swap。記憶體吃緊時的 KV cache 量化（K=Q8 / V=Q4）見 [模組五 VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/)。

## Flash Attention：記憶體高效實作

Flash Attention（Dao et al., 2022）是 attention 的 GPU 高效實作。標準 attention 在記憶體中具體實作 `(seq_len, seq_len)` 矩陣、長 context 時記憶體爆炸（10K context = 100M 個 float）。

Flash Attention 用「tiling + recompute」技巧、把 attention 拆成 block 算、不具體實作完整 attention matrix。記憶體佔用從 O(n²) 降到 O(n)、速度也快 2 ~ 4 倍。

Apple Silicon 上的對應實作可能稱為 Metal FlashAttention 或類似名稱、Ollama、LM Studio、oMLX 等本地推論伺服器逐步整合。

Flash Attention 何時收益有限：

- **短 context 場景**：seq_len < 1K 時、attention matrix 本身就小、Flash Attention 的記憶體節省無感。
- **CPU 推論**：Flash Attention 的 tiling 設計針對 GPU memory hierarchy（HBM ↔ SRAM）、CPU 上的記憶體層級不同、收益遠小於 GPU。
- **配合 GQA 的場景**：GQA 已大幅減少 KV cache、Flash Attention 的相對收益縮小。

## Grouped Query Attention（GQA）

Grouped Query Attention 是 multi-head attention 的變體、減少 KV cache 佔用。核心想法：「不同 head 共用 K、V、只有 Q 各自獨立」。

| 變體                          | Q heads | K/V heads | 特性                               |
| ----------------------------- | ------- | --------- | ---------------------------------- |
| Multi-Head Attention (MHA)    | N       | N         | 標準、各 head 完全獨立             |
| Multi-Query Attention (MQA)   | N       | 1         | 所有 head 共用一組 K/V、最省記憶體 |
| Grouped Query Attention (GQA) | N       | K (K < N) | 折衷、品質接近 MHA、KV cache 較小  |

Llama 3 / Gemma 4 / Qwen3 都用 GQA、把 KV cache 大小減半到三分之一、長 context 場景受益。

## 為什麼 speculative decoding 在 code 場景加速明顯：attention 並行性的支撐

加速本身來自 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) / [MTP](/llm/knowledge-cards/mtp/)、attention 在這條路徑上的角色是「提供並行驗證所需的計算結構」：

- Speculative decoding 一次驗證 N 個 token、需要 attention 同時處理 N 個 query 對前面所有 K/V。
- Attention 機制天生可並行、一次 forward pass 驗證 N 個 token 跟驗證 1 個 token 的時間接近（瓶頸是讀權重而非算 attention）。
- 寫 code 場景 drafter 接受率高（code 的 pattern 容易預測）、加速明顯。

理解這點、能解釋為什麼 MTP 對 coding 比創意寫作加速更明顯：差別不在 attention 本身、在「drafter 預測的接受率」這個 sampling 層的變數。

## 小結

Attention 是 Transformer 的核心、每個 token 用 Q / K / V 機制決定該關注前面哪些 token。Scaled dot-product attention 是基本公式、multi-head 並行多個 attention、causal mask 強制只看前面、KV cache 避免重複計算、Flash Attention 與 GQA 是現代效率優化。理解 attention 後、看 LLM 內部運算就有完整地圖。

下一章：[3.3 Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)、把 attention 跟 embedding 組裝成完整模型。
