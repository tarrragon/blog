---
title: "4.8 Embedding model 內部：訓練、選型、in-domain fine-tune"
date: 2026-05-12
description: "Embedding model 怎麼訓練（contrastive learning + hard negative mining）、怎麼挑（MTEB / 大小 / domain）、何時該自己 fine-tune"
tags: ["llm", "applications", "embedding", "rag", "evaluation"]
weight: 8
---

[RAG](/llm/04-applications/rag-principles/) 章節定義了 retrieval + augmentation 的二段式結構、但 retrieval 階段背後的 [embedding model](/llm/knowledge-cards/embedding-model/) 怎麼運作、怎麼選、什麼時候該換、什麼時候該自己 fine-tune、這些決策直接影響 RAG 品質。本章把 embedding model 的訓練機制、評估方法、實務選型展開。

## 本章目標

讀完本章後、你應該能：

1. 解釋 embedding model 跟 base LLM 的訓練差異。
2. 看到 MTEB / BEIR 分數時、知道對自己場景的意義。
3. 對自己 domain 選對 embedding model（通用 vs code vs multilingual）。
4. 判斷「需要 fine-tune 自己的 embedding model」的時機跟方法。

## Embedding model vs LLM 的訓練差異

兩者底層架構可能類似（都用 Transformer）、但訓練 objective 完全不同：

| 維度            | LLM（如 Llama / Gemma instruct） | Embedding model（如 bge-large、jina-v3）                           |
| --------------- | -------------------------------- | ------------------------------------------------------------------ |
| 訓練 objective  | Next-token prediction + RLHF     | [Contrastive learning](/llm/knowledge-cards/contrastive-learning/) |
| 輸出形式        | 一連串 token                     | 一個固定維度的向量（如 768、1024）                                 |
| 訓練資料        | Trillion-token 通用文字          | 億級的 (query, doc) 正向對                                         |
| 用法            | Prompt → response                | Text → vector                                                      |
| Pretrained 起點 | 從 scratch 或繼承 base           | 通常從 base LLM 抽 hidden state 開始                               |

關鍵理解：**不能拿任意 LLM 的最後 hidden state 當 embedding** — LLM hidden state 是為「預測下一個 token」優化、不為「相似度比較」優化。要再經過 contrastive learning fine-tune 才能當 embedding model 用。

Embedding model 的典型訓練 pipeline：

```text
Stage 1: 從 base model 開始（如 BERT、RoBERTa、Mistral、Llama）
   ↓
Stage 2: Contrastive pre-training
   用大量 weak supervised pair（如 Reddit title-body、StackExchange QA）
   InfoNCE loss、batch size 大、hard negative mining
   ↓
Stage 3: Supervised fine-tune
   用標註好的 (query, relevant_doc) pair
   來源如 MSMARCO、Natural Questions
   ↓
Stage 4（可選）: Task-specific instruction tuning
   讓模型懂「task description」、可針對不同 retrieval 任務切換
   代表：bge-large、e5-mistral-7b-instruct
```

Stage 4 的「instruction-tuned embedding」是 2024 後流行的設計：query 前加「Represent this sentence for retrieving relevant passages:」這類前綴、embedding model 學會依任務調整向量。

## 選型維度

主流 embedding model 的選型維度：

### 1. Domain 相符

| Domain               | 推薦模型                                    | 為什麼                                              |
| -------------------- | ------------------------------------------- | --------------------------------------------------- |
| 通用英文             | bge-large-en-v1.5、mxbai-embed-large-v1     | 通用 corpus、MTEB Retrieval 高分                    |
| 通用多語             | jina-embeddings-v3、bge-m3、multilingual-e5 | 多語 pretrain、中日韓阿等支援                       |
| Code（讀 / 寫 code） | jina-embeddings-v2-base-code、voyage-code-3 | code corpus 訓練、語意（函式名、註解）+ syntax 結合 |
| 中文                 | bge-large-zh、Conan-embedding               | 中文 corpus 為主                                    |
| 跨語言（中英混合）   | jina-embeddings-v3、multilingual-e5         | 跨語言對齊訓練、中英 query 找對方語言 doc           |

### 2. 大小（模型大小 / 向量維度）

| Tier           | 模型大小                             | 向量維度  | Latency / 記憶體         | 適合場景                     |
| -------------- | ------------------------------------ | --------- | ------------------------ | ---------------------------- |
| 小（< 200M）   | nomic-embed (137M)、all-MiniLM (23M) | 384-768   | 快、本機 CPU 可跑        | 本地 RAG、簡單 retrieval     |
| 中（200-500M） | bge-large (335M)、mxbai-embed-large  | 1024      | 中、需要 GPU 或 fast CPU | 主力 RAG、品質敏感場景       |
| 大（500M-7B）  | e5-mistral-7b、Linq-Embed-Mistral    | 4096      | 慢、需要 GPU             | 高品質、雲端、Reranking 場景 |
| 雲端 API       | OpenAI text-embedding-3、voyage-3    | 1024-3072 | 網路 latency + API 成本  | 雲端 RAG、高 QPS             |

### 3. Context window 上限

不同 embedding model 對單次 embed 的 token 上限不同：

| 模型                       | Context limit  |
| -------------------------- | -------------- |
| 早期 sentence-transformers | 256-512 tokens |
| bge-large / mxbai-embed    | 512 tokens     |
| nomic-embed-text-v1.5      | 8192 tokens    |
| jina-embeddings-v3         | 8192 tokens    |
| voyage-3                   | 32K tokens     |

> **事實查核註**：本節所列具體型號（bge-large-en-v1.5、jina-embeddings-v3、nomic-embed-text-v1.5、voyage-3 等）、向量維度、context limit、訓練資料 domain、MTEB / BEIR 排名 — 都是 2026/5 主流版本的估計、各模型升級節奏快、引用前以 [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) 跟對應 model card 當前狀態為準。

選擇影響 chunking 策略（見 [4.0 RAG](/llm/04-applications/rag-principles/) 的 chunking 段）：短 context embedding 要切細、長 context embedding 可保留更完整段落、但內部 attention 對長段中段仍可能 lost-in-the-middle。

### 4. Cosine similarity 設計

部分 embedding model 訓練時就 L2-normalized、用 cosine = dot product；部分沒 normalize、要自己處理：

| Model                  | Normalize 預設  | 推薦 distance metric               |
| ---------------------- | --------------- | ---------------------------------- |
| bge-large、mxbai-embed | 已 L2-normalize | Dot product（高效、結果同 cosine） |
| nomic-embed-text       | 已 L2-normalize | Dot product                        |
| OpenAI ada-002 / 3     | 已 L2-normalize | Dot product                        |
| 自訓練 / 早期模型      | 未 normalize    | Cosine similarity                  |

> 詳細見 [vector-norm](/llm/knowledge-cards/vector-norm/) 跟 [dot-product](/llm/knowledge-cards/dot-product/) 卡片。

## 評估：MTEB 跟自己 domain 的對齊

[MTEB](/llm/knowledge-cards/mteb-benchmark/) 是現在挑選 embedding model 最常用的 leaderboard、但要正確讀：

1. **看 Retrieval 子分數、不是 Overall**：MTEB 含 8 大類、跟 RAG 最直接相關的是 Retrieval 跟 Reranking
2. **跟自己 domain 對齊**：MTEB 通用 corpus、自己 domain 可能跟 MTEB 落差大
3. **In-domain benchmark 才是 final test**：用自己工作流的真實 query 跟 expected doc、自建小型評估集（如 100-200 對）、看候選 embedding model 的 hit rate / nDCG

In-domain 評估的最小可行流程：

```python
# 偽代碼
1. 蒐集 50-100 個 query + expected_doc（已知答案的對）
2. 對 candidate embedding models 各跑：
   - embed 所有 doc（含 expected 跟 distractor、~1000 個 distractor）
   - embed 每個 query
   - 算 query-doc similarity、看 expected 是否在 top-5 / top-10
3. 比較 candidate 的 hit_rate@5 / hit_rate@10
```

跑完這個再決定用哪個 embedding model、比看 MTEB leaderboard 可靠很多。

## 何時該 fine-tune 自己的 embedding model

通常**不該** fine-tune embedding model — 用現成的 bge-large、jina-v3 已經很好。但下列情境值得評估：

1. **Domain 跟通用 corpus 差距大**：
   - 醫療 / 法律 / 金融的專業術語、通用 embedding model 對「同義詞」「同概念不同表述」recall 差
   - In-domain term frequency 跟通用 corpus 差距大（如「IRA」在金融 vs 政治語境）

2. **In-domain benchmark hit rate 顯著低於通用 benchmark**：
   - 用 MTEB 高分模型、in-domain hit rate@5 仍 < 60%
   - 換多個候選 embedding model、所有都類似低分

3. **有足夠 in-domain (query, doc) 對**：
   - Fine-tune 需要至少數千對、最好 1-10 萬對
   - 對少於 1000 對的場景、fine-tune 收益通常低於數據增強 / 提升 retrieval pipeline

Fine-tune 流程（簡化）：

```text
1. Collect in-domain (query, doc) pairs（或 (anchor, positive, negative) triplets）
2. 用 sentence-transformers library 或 Hugging Face PEFT
3. LoRA fine-tune（不全參數 fine-tune、保留通用能力）
4. Loss：MultipleNegativesRankingLoss、InfoNCE 等
5. Hard negative mining：用初版模型 retrieve top-50、人工 / LLM 標註哪些是 hard negative
6. Iterate：fine-tune → 重 mine hard negatives → re-fine-tune
```

## 跟 LLM 的整合：retrieval pipeline

完整 RAG pipeline 裡 embedding model 的位置：

```text
[Ingestion 階段（離線）]
  Documents
    ↓ chunking
  Chunks
    ↓ embedding model
  Chunk vectors → 存進 vector DB

[Query 階段（線上）]
  User query
    ↓ embedding model
  Query vector
    ↓ vector DB ANN search
  Top-K chunks
    ↓ (optional) reranking
  Top-N chunks
    ↓ augment LLM prompt
  LLM response
```

關鍵設計決策：

1. **Embedding model 一致性**：ingestion 跟 query 必須用同個 model（換 model = 整批 re-embed）
2. **Chunking 策略對齊 embedding context**：見 [4.0 RAG chunking](/llm/04-applications/rag-principles/)
3. **Reranking model 通常用 cross-encoder**：embedding model 是 bi-encoder（query 跟 doc 分開 embed）、reranker 是 cross-encoder（query + doc 一起算）、品質更高但慢、適合在 top-50 → top-5 之間做 reranking
4. **Hybrid retrieval**：BM25（字面）+ embedding（語意）混用、用 RRF（Reciprocal Rank Fusion）合併、是 production 常見配置

## 本地 vs 雲端 embedding

| 維度          | 本地（如 nomic-embed）             | 雲端（如 OpenAI text-embedding-3）  |
| ------------- | ---------------------------------- | ----------------------------------- |
| 隱私          | 完全本地、no exfil                 | API 送 doc、依政策 log              |
| 成本          | 一次硬體 + 電費                    | 按 token 計費、長期可累積           |
| 品質          | bge-large / jina-v3 已接近雲端旗艦 | 略高（旗艦如 voyage-3 仍領先）      |
| Latency       | 視硬體、本地 SSD 快                | 網路 latency                        |
| 多語 / domain | 開源選擇多、可挑 domain-specific   | API 是通用、不一定最佳 domain match |

寫 code 場景的判讀：

- **codebase 內部 RAG（NDA / 機密 code）**：本地 embedding 必選
- **個人開源專案 RAG**：本地 embedding 是合理 default、簡單、free
- **公司內部 RAG（需高品質、量大）**：評估 voyage-3 / OpenAI v3 vs 本地 bge-large
- **產品級 production RAG**：通常雲端 API + 自己 fine-tune 的 embedding（最佳品質）

## 何時過時 / 何時不過時

**不會過時的部分**：

- Contrastive learning 是 embedding model 的核心訓練 paradigm
- MTEB 作為通用 embedding 評估的角色
- 「跟自己 domain 對齊」的 in-domain benchmark 必要性
- Bi-encoder vs cross-encoder 的分工（retrieval vs reranking）
- Hybrid retrieval（BM25 + embedding）的設計

**會變的部分**：

- 具體 embedding model（bge → bge-v2 → ...、jina-v3 → v4 → ...）
- MTEB leaderboard 排名（每月變）
- Instruction-tuned embedding 的 prompt format（標準化中）
- Embedding model 的 context window 上限（推升中）
- Long-context embedding 的研究（如 ColBERT-style late interaction）

## 小結

Embedding model 是 RAG 品質的核心驅動。訓練 paradigm 是 contrastive learning + hard negative mining、跟 LLM 的 next-token prediction 不同。選型看 domain、大小、context limit、normalize 預設；MTEB 是參考、in-domain benchmark 是 final test。Fine-tune 通常不需要、特殊 domain 且資料足夠才考慮。本地 vs 雲端的選擇看隱私 / 成本 / 品質需求。

下一章：[4.9 Benchmarking 與評估方法論](/llm/04-applications/benchmarking-and-evaluation/)、看怎麼判讀 LLM benchmark 數字、自己跑 benchmark 的方法。
