---
title: "2.0 線性代數：向量、矩陣、空間"
date: 2026-05-11
description: "LLM 內部運算的基底：向量、矩陣、向量空間、內積、norm、矩陣乘法的角色"
tags: ["llm", "math", "linear-algebra"]
weight: 0
---

線性代數是 LLM 內部運算的基底。每一次模型 forward pass、本質上都是一連串矩陣乘法；每個 [token](/llm/knowledge-cards/token/) 在模型內部都是一個向量；attention 機制計算「相關性」的方式就是向量內積。理解這幾個概念、能讓「為什麼模型有 31B 個參數」「為什麼推論需要這麼多記憶體」「為什麼 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 是瓶頸」從口號變成可推導的事實。

本章假設你看過向量這個詞、知道矩陣有 row 跟 column、但忘記中間細節。每個概念給出定義、在 LLM 中的角色、實務上會怎麼遇到它。

## 本章目標

讀完本章後、你應該能：

1. 用向量描述「token 在語意空間中的位置」。
2. 用矩陣乘法解釋「模型一個 layer 在做什麼」。
3. 估算「31B 模型佔多少記憶體」（除了量化外的計算依據）。
4. 看到「dimension mismatch」錯誤時、知道是維度沒對齊。

## 向量：有方向有長度的數列

向量（vector）的核心定義是「有序的數字序列」。在 LLM 中、每個 token 對應一個向量、稱為 embedding；向量的維度（dimension）通常是幾百到幾千、例如 Gemma 4 的 hidden size 約 4096。

向量可以幾何解釋成「N 維空間中的一個箭頭」、方向跟長度都重要：

- **方向**：表示「token 的語意特徵」。語意相近的 token（如 `cat` 跟 `kitten`）向量方向接近、語意無關的（如 `cat` 跟 `algorithm`）方向遠。
- **長度**（norm）：表示「token 在這個維度上的強度」、計算方式有 L1（絕對值總和）、L2（平方和開根號、最常用）、L∞（最大絕對值）等。

實務上會遇到向量的地方：

- [Embedding 模型](/llm/knowledge-cards/embedding-model/) 把文字轉成向量、Continue.dev 的 `@codebase` 用這個機制找相關片段。
- [KV cache](/llm/knowledge-cards/kv-cache/) 存的就是每個 token 在每個 layer 算出來的向量。
- 模型內部所有 token 都以向量形式流動、token 本身的整數 ID 只在輸入跟輸出端用到。

## 內積：衡量兩個向量的相關性

內積（dot product / inner product）的核心定義是「兩個向量對應位置相乘再相加」。`a · b = a₁b₁ + a₂b₂ + ... + aₙbₙ`。

內積的幾何意義是「投影」：a 在 b 方向上的長度乘以 b 的長度。對 LLM 而言、它最重要的用途是衡量兩個向量的相似度：

- 兩個向量方向接近、內積大（正值）。
- 兩個向量垂直、內積為 0。
- 兩個向量方向相反、內積大負值。

Attention 機制就是用內積算「當前 token 該關注前面哪幾個 token」：

```text
attention_score = query · key  ← 內積
```

每一對 (query, key) 算一次內積、得到一個分數；分數高表示「這個 token 該注意那個位置」。詳細展開見 [3.2 attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)。

## Norm：向量的長度

Norm（範數）的核心定義是「衡量向量大小的純量值」。最常用的 L2 norm（也叫 Euclidean norm）：

```text
||v||₂ = sqrt(v₁² + v₂² + ... + vₙ²)
```

LLM 中 norm 的用途：

- **Layer normalization**：每個 layer 結束後把 activation（每層輸出的數值、見 [3.0 神經網路基礎](/llm/03-theoretical-foundations/neural-network-basics/)）重新正規化、避免數值爆炸或消失。
- **Embedding normalization**：embedding 模型常把向量正規化到 L2 norm = 1、讓內積等同於 cosine similarity。
- **Gradient clipping**：訓練時若 gradient（訓練階段更新權重用的方向、見 [2.2 微積分與最佳化](/llm/02-math-foundations/calculus-and-optimization/)）的 norm 太大、截斷到合理範圍、避免訓練不穩。

Cosine similarity（餘弦相似度）= 兩個向量的內積除以兩者 norm 的乘積、結果落在 -1 到 1 之間、是 RAG / semantic search 最常用的相似度指標。實務上常先把 embedding 正規化到 L2 norm = 1、之後 cosine similarity 退化為單純內積、可直接套用 dot-product 比對。

使用 cosine similarity 時的兩個邊界：

- **Anisotropy（向量集中在某方向）**：訓練不充分或 embedding 維度太低時、所有向量會擠在一個窄錐裡、cosine 分數普遍偏高、相對排序失準。判讀訊號：抽樣 100 對隨機 query、cosine score 平均 > 0.7。修法：換較強的 embedding model、或對 embedding 做 mean-centering / whitening。
- **不同 embedding space 不可比**：nomic、OpenAI、bge 訓練 objective 不同、向量空間不同源、跨模型算 cosine 沒意義。修法：同一個 retrieval pipeline 鎖一個 embedding model、換模型時整批重算 index。

## 矩陣：把向量打包成 2D 結構

矩陣（matrix）的核心定義是「向量的有序集合、以 2D table 形式組織」。一個 m × n 矩陣有 m row、n column；每個 row 或 column 可以視為向量。

LLM 中的矩陣到處都是：

- **權重矩陣**：每個 linear layer 對應一個權重矩陣 W、shape 是 `(input_dim, output_dim)`。
- **Batched inputs**：把多個 token 的 embedding 打包成 `(seq_len, embed_dim)` 矩陣、一次處理。
- **Attention scores**：每對 (query, key) 算內積、得到 `(seq_len, seq_len)` 矩陣。

模型權重數量的算法：把所有 layer 的權重矩陣大小加總、就是 31B / 70B 等參數規模。例如一個 hidden size = 4096 的 linear layer、權重矩陣大小 `4096 × 4096 = 16,777,216`、約 16.8M 參數。31B 模型的數字推導：~1800 個這個量級的權重矩陣相加（attention 的 Q / K / V / O 矩陣 + FFN 的兩個矩陣 × 數十個 transformer block）、總和約 31B 個參數；bf16 每權重 2 bytes、整份權重約 62GB；Q4 量化後每權重 0.5 bytes、約 18GB。完整的記憶體預算判讀見 [0.5 Apple Silicon 記憶體預算](/llm/00-foundations/hardware-memory-budget/)。

## 矩陣乘法：LLM 推論的核心運算

矩陣乘法（matrix multiplication）的核心定義是「左矩陣的 row 跟右矩陣的 column 做內積、結果填進對應位置」。對 `A (m × k)` 跟 `B (k × n)` 相乘、得到 `C (m × n)`、其中 `C[i][j] = A 的第 i row 跟 B 的第 j column 的內積`。

LLM 推論的每個 layer 都是矩陣乘法 + 非線性 activation。例如一個 feed-forward 層的計算是：

```text
output = activation(input @ W₁) @ W₂
```

其中 `@` 是矩陣乘法、`W₁`、`W₂` 是權重矩陣。一個 31B 模型跑一次 forward pass、會做數百次矩陣乘法、總運算量是「token 數 × 模型參數數 × 2」的量級。

矩陣乘法的維度規則：**左矩陣的 column 數要等於右矩陣的 row 數**。`(m × k) @ (k × n) = (m × n)`。遇到 dimension mismatch 錯誤的定位流程：讀 traceback 找到 `mat1` / `mat2` 各自的 shape、檢查倒數第二維（左）跟倒數第一維（右）是否相等；常見來源是 batch dim 沒 squeeze、或 transpose 順序錯。理論上限 ≈ 30 tok/s 是 dense 模型 + 單請求 + 無 batching / 無 speculative decoding 的純 memory-bound 情境下的估算、實際數字隨量化、framework、batch 配置浮動。

## 為什麼這對 memory bandwidth 重要

[Memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 是 LLM 推論的真實瓶頸、原因落在矩陣乘法本身：

- 每生成一個新 token、需要把整個模型權重（所有矩陣）從記憶體讀到處理器一次。
- 算力（FLOPs）在現代 GPU / Apple Silicon 上充足、瓶頸落在「讀權重要多久」。
- 31B 模型約 18GB（Q4 量化）、M4 Max 頻寬 546 GB/s、理論上限 ≈ 30 tok/s。

這就是為什麼 [量化](/llm/knowledge-cards/quantization/) 能加速：權重變小、每秒能讀過更多次完整模型、tok/s 變高。也是為什麼 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 能加速：一次 forward pass 就把權重讀過一次、驗證多個 token、攤平單 token 成本。

## 張量（Tensor）：多維度的矩陣

張量（tensor）的核心定義是「N 維陣列、矩陣是 N=2 的特例」。LLM 內部常用 3D / 4D tensor：

- **3D**：`(batch_size, seq_len, hidden_dim)`、表示「N 個句子、每個句子 M 個 token、每個 token 是 D 維向量」。
- **4D**：`(batch_size, num_heads, seq_len, head_dim)`、表示 multi-head attention 的並行計算結構。

PyTorch、MLX 等 framework 的核心型別都叫 Tensor、所有運算（矩陣乘法、norm、softmax 等）都對 tensor 做。

## 小結

線性代數提供 LLM 內部運算的詞彙：向量是 token 的內部表示、內積算相關性、矩陣乘法是每個 layer 的核心、張量是把這些打包成可批次處理的結構。後續章節（[機率與資訊論](/llm/02-math-foundations/probability-and-information/)、[最佳化](/llm/02-math-foundations/calculus-and-optimization/)）會在這個基底上建立 LLM 訓練與推論的完整數學圖像。

想看完整推導跟練習、見 [2.4 公開課推薦](/llm/02-math-foundations/going-deeper-math/) 的 MIT 18.06、3Blue1Brown 線性代數系列等資源。

下一章：[2.1 機率與資訊論](/llm/02-math-foundations/probability-and-information/)。
