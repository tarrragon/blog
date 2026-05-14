---
title: "3.1 Embedding 空間"
date: 2026-05-11
description: "token 怎麼變成向量、為什麼相似 token 在向量空間中靠近、embedding 是怎麼學出來的"
tags: ["llm", "theory", "embedding"]
weight: 1
---

Embedding 是 LLM 把離散 [token](/llm/knowledge-cards/token/) 轉成連續向量的關鍵步驟。模型內部的每一層運算都對向量做、token 本身的整數 ID 只在 input / output 端用到。理解 embedding 怎麼運作、能解釋「為什麼模型能理解 token 之間的語意關係」「為什麼 [embedding 模型](/llm/knowledge-cards/embedding-model/) 能做 semantic search」「為什麼不同 model 的 embedding 互不相容」。

本章拆開 embedding 的三件事：怎麼從 token ID 變成向量、向量空間怎麼承載語意、embedding 是怎麼學出來的。

## 本章目標

讀完本章後、你應該能：

1. 解釋 embedding layer 在 LLM 中的位置。
2. 看到「embedding dimension = 4096」時、知道指什麼。
3. 解釋 RAG / semantic search 為什麼用 embedding similarity。
4. 區分 [word2vec](/llm/knowledge-cards/word2vec/)、句子 embedding、contextual embedding 的差別。

## [Embedding Layer](/llm/knowledge-cards/embedding-layer/)：從 token ID 到向量

Embedding layer（嵌入層）的核心結構是「一個 lookup table、把 token ID（整數）map 到向量」。形式上是一個 `(vocab_size, hidden_dim)` 的矩陣 E：

```text
token_id = 12345
embedding = E[12345]   ← 取出第 12345 row、得到 hidden_dim 維向量
```

Gemma 4 31B 的 embedding matrix：

- vocab_size = 256,000
- hidden_dim = 5120
- 總參數 = 256,000 × 5120 ≈ 1.3 billion

光是 embedding layer 就佔 31B 中的 1.3B（約 4%）。70B 模型的 embedding layer 更大、可達 2B 以上。

實作上 embedding lookup 比矩陣乘法便宜（只是查表）、但記憶體佔用顯著。

## 向量空間：用 hidden_dim 維空間編碼語意

Embedding 的設計目標是「讓相似 token 在向量空間中靠近、不相似的遠」。具體用[內積](/llm/02-math-foundations/linear-algebra-for-llm/) 或 cosine similarity 衡量相似度：

```text
cosine_sim(a, b) = (a · b) / (||a|| × ||b||)
```

訓練後的 embedding 會展現語意結構：

- `embedding(cat)` 跟 `embedding(kitten)` 內積大。
- `embedding(cat)` 跟 `embedding(algorithm)` 內積小。
- 著名的「king - man + woman ≈ queen」現象（word2vec 時代發現、Transformer 上也成立）。

這個性質讓 embedding 能做：

- **Semantic search**：把 query 跟 documents 都轉成 embedding、用 cosine similarity 找相似的。
- **RAG**：把 codebase chunks embed、用 query embedding 找相關片段。
- **Clustering**：embedding 上跑 k-means、把語意相近的 document 分組。
- **Anomaly detection**：embedding 離 cluster 中心遠的就是異常。

## Embedding 怎麼學出來

Embedding layer 跟其他 layer 一樣、是訓練過程中學出來的。具體機制：

1. 訓練初期 embedding 是隨機初始化。
2. Forward pass 用這些 embedding 跑模型、預測下一個 token。
3. 預測錯了、loss 大、[backprop](/llm/02-math-foundations/calculus-and-optimization/) 算 gradient、更新 embedding。
4. 反覆 trillion token 訓練、embedding 收斂到能表達語意。

訓練機制讓「常在類似 context 出現的 token」拿到相似的 embedding。例如 `cat` 跟 `kitten` 在訓練資料中常出現在類似句子（「The ___ is sleeping」「I have a pet ___」等）、模型最佳化的方向會自然讓兩者的 embedding 接近。

這就是「distributional semantics」（分佈式語意）的核心假設：**字詞的意義由它周圍的字詞決定**（"You shall know a word by the company it keeps", J. R. Firth, 1957）。

## Word2Vec：embedding 的早期實作

Word2Vec（Mikolov et al., 2013）是 embedding 的經典實作、影響後續所有 NLP。它的核心是「用淺層網路專門學 embedding」、不做下游任務：

- **Skip-gram**：給一個中心字、預測周圍字。
- **CBOW**：給周圍字、預測中心字。

訓練後 embedding 展現語意結構（包括「king - man + woman ≈ queen」這個著名實驗、近年研究指出該類比有 cherry-picking 質疑、Linzen 2016 / Nissim et al. 2020、是入門啟發、非嚴格 evidence）。Word2Vec 在大型語意理解場景已被 contextual embedding 取代、但在「靜態查表、邊緣計算、輕量 baseline」等情境仍有用、不是完全淘汰。

## Word-level vs Contextual Embedding

Word-level embedding（Word2Vec、GloVe 等）每個字一個固定向量、不考慮 context：

- `bank` 在「river bank」跟「bank account」中拿到同樣的 embedding。
- 簡單、可預先計算、查表快。
- 限制：無法區分多義詞。

Contextual embedding（BERT、GPT 等 Transformer-based）的向量隨 context 改變：

- `bank` 在「river bank」跟「bank account」中拿到不同的向量。
- 模型每層輸出都可視為一種 contextual embedding、越深越抽象。
- 缺點：需要跑完整模型、不能預先計算。

LLM 內部用的是 contextual embedding。輸入端的 embedding layer 是 word-level（每個 token ID 對應固定向量）、但經過 attention 後變成 context-dependent。

## Sentence / Paragraph Embedding

句子或段落級別的 embedding 是把整段文字壓成一個向量、用於 retrieval 與分類任務。常見實作：

| 模型                    | 特性                                 |
| ----------------------- | ------------------------------------ |
| Sentence-BERT (SBERT)   | 用 siamese BERT 訓練、retrieval 經典 |
| nomic-embed-text        | 開源、Continue.dev 預設              |
| OpenAI text-embedding-3 | 商業 API、品質高                     |
| BGE / E5 系列           | 多語言、SOTA 開源                    |

[Embedding 模型](/llm/knowledge-cards/embedding-model/) 跟 chat model 是不同訓練流程：

- Chat model 學「下個 token 機率分佈」。
- Embedding model 學「整段文字壓成一個向量、用 cosine similarity 衡量語意相似度」。

兩者底層架構都是 Transformer、但訓練 objective 不同、得到的向量空間不通用。

## 向量空間互不相容

不同 embedding 模型的向量空間互不相容：

- nomic-embed-text 輸出 768 維向量。
- OpenAI text-embedding-3-small 輸出 1536 維向量。
- 兩者各自的座標軸有獨立意義、不能拿 nomic 的向量跟 OpenAI 的向量算 cosine。

實務啟示：

1. 換 embedding 模型要重建 vector database。
2. 一個 retrieval 系統用同一個 embedding 模型 throughout、混用會壞。
3. 模型升級時要 backfill 舊資料。

## Embedding similarity 的失效情境

Embedding similarity 在多數 retrieval / semantic search 場景能用、但有幾類已知失效模式、影響 RAG / `@codebase` 的回答品質：

| 失效模式                   | 判讀訊號                                              | 修法                                                                    |
| -------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------- |
| Anisotropy（向量擠在窄錐） | 隨機 query 對的 cosine score 平均 > 0.7、相對排序失準 | 換較強 embedding model、做 mean-centering / whitening 後處理            |
| 否定句被當相似             | 「我能買牛奶」跟「我不能買牛奶」cosine 接近           | 結構性區分 / 補 BM25 lexical retrieval 取交集、或用 reranker 做最終排序 |
| Lexical mismatch           | query 用同義詞、retrieval 找不到原文                  | 加 hybrid retrieval（embedding + BM25）、或在 query expansion 做改寫    |
| 長尾稀有詞                 | 專有名詞 / 縮寫 / domain 術語 retrieval 結果飄        | 跑 domain fine-tune embedding、或保留 BM25 作為 backup 排序             |
| 跨語言混合 token           | 中英混雜文件查不準                                    | 用多語言 embedding（BGE-m3 / multilingual-e5）取代英文 only embedding   |

實作層級的修法多半是 hybrid retrieval（embedding + BM25 / TF-IDF 各跑一次、合併分數）或加 reranker 做最終排序、純依賴 cosine similarity 風險高的場景值得納入這層。

## 位置編碼：把順序資訊加進 embedding

純 embedding layer 沒有「順序資訊」、`[cat, dog]` 跟 `[dog, cat]` 的 embedding 序列只是 order 不同的 set。Transformer 用 [positional encoding](/llm/knowledge-cards/positional-encoding/) 把位置資訊加進去。

主流位置編碼方法：

| 方法       | 機制                                                          | 主要使用模型 / 取捨                                         |
| ---------- | ------------------------------------------------------------- | ----------------------------------------------------------- |
| Sinusoidal | 用 sin / cos 不同頻率生成固定位置向量、加進 embedding         | 原始 Transformer paper、現已少見、長度外推能力弱            |
| Learned    | 學一個 `(max_seq_len, hidden_dim)` 的位置矩陣、加進 embedding | GPT-2 / BERT 系列、被綁死在訓練長度、無法外推               |
| RoPE       | Rotary Position Embedding、把位置編碼到 Q/K 的旋轉中          | Llama / Gemma / Qwen 主流、長度外推能力佳、實作上是相對位置 |
| ALiBi      | Attention with Linear Biases、在 attention scores 加位置 bias | MPT 系列、長度外推極佳、但 LLM 主流仍偏 RoPE                |

RoPE 是 2026 年的主流選擇。詳細展開見 [3.3 Transformer 架構](/llm/03-theoretical-foundations/transformer-architecture/)。

## Tied vs Untied Embedding

「Tied embedding」指「input embedding（token → vector）跟 output projection（hidden → logits）共用同一個矩陣」。實作上 input embedding 矩陣 `E` 的 shape 是 `(vocab_size, hidden_dim)`、output projection 矩陣的 shape 是 `(hidden_dim, vocab_size)`；tied 模式直接用 `E^T`（轉置）當 output projection、省下一份 `(vocab_size, hidden_dim)` 大小的權重。GPT-2 系列預設 tied、節省參數。

「Untied embedding」是兩者各自獨立、各自訓練。Llama 系列預設 untied、品質略好（兩個矩陣可以各自最佳化）、但 embedding layer 跟 output layer 都要存。

實務上、大模型（30B+）幾乎都採 untied、用較多參數換較高品質；小模型（1B 以下）為了壓縮參數量仍會 tied。

## Embedding 在 LLM forward pass 中的位置

LLM 的 forward pass 概略：

```text
tokens (整數序列)
  ↓ embedding lookup
embeddings (向量序列、shape: [seq_len, hidden_dim])
  ↓ + positional encoding
positioned embeddings
  ↓ Transformer block × N
final hidden states
  ↓ output projection
logits (shape: [seq_len, vocab_size])
  ↓ softmax
機率分佈
```

每個 Transformer block 內部都對向量做變換、向量維度保持 hidden_dim 不變、只有 input embedding 跟 output projection 在 vocab_size 跟 hidden_dim 之間轉換。

## 小結

Embedding 是 LLM 把離散 token 轉成連續向量的機制、讓「語意」可以用向量空間幾何衡量。Word-level embedding（Word2Vec）是早期實作、現代 LLM 用 contextual embedding。Embedding 模型跟 chat model 是不同訓練流程、向量空間互不相容。理解 embedding 的角色、能解釋 RAG、semantic search、`@codebase` 命令等實務應用的底層機制。

下一章：[3.2 attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)、Transformer 的招牌技術。
