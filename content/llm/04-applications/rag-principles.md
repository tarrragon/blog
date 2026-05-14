---
title: "4.1 RAG 原理：retrieval + augmentation 模式"
date: 2026-05-11
description: "為什麼模型需要外掛知識、語意相似 vs 字面相似、chunking 的本質取捨、retrieval 失敗的根本原因"
tags: ["llm", "applications", "rag", "embedding"]
weight: 1
---

[RAG](/llm/knowledge-cards/rag/)（Retrieval-Augmented Generation）的核心是「給 LLM 動態外掛一份知識、讓它在生成時拿這份知識當 context」。它的存在解的是 LLM 「靜態參數記憶」的根本限制：模型訓練完之後權重就凍結、無法存取訓練資料外的事實、無法看到 cutoff 之後發生的事、也無法存取私有資料。

本章把 RAG 拆成不會隨工具世代消失的部分：retrieval 的本質、chunking 的取捨、失敗模式的分類、跟 fine-tuning / long context 三種路線的比較。LangChain、LlamaIndex、Vector database 選型等具體實作不在本章範圍——這些半年一個版本、教程價值低於壽命。本章寫的是「為什麼 retrieval 會這樣設計、什麼時候會失敗、什麼時候改用其他方案」。

## 本章目標

讀完本章後你能：

1. 解釋為什麼 LLM 需要外掛知識、純靠模型參數記憶解不了什麼問題。
2. 區分「語意相似」與「字面相似」對 retrieval 的影響、看到 retrieval 結果不理想時、判斷是哪一類失配。
3. 看到 chunking 參數時、知道背後的 resolution vs context 取捨。
4. 在「RAG / fine-tuning / long context」三者之間、依任務做合理選擇。

## 為什麼模型需要外掛知識

LLM 的參數記憶是「壓縮過的訓練資料」：權重把預訓練看過的所有文字壓進一個固定大小的數值結構、推論時用這份壓縮表示生成下一個 token。這個結構有三個天然限制：

1. **訓練 cutoff**：模型只認識訓練資料截止前的世界、cutoff 之後發生的事完全看不見。Claude 4 cutoff 是 2026/1、2026/5 的新聞模型不知道。
2. **私有資料缺席**：訓練資料是公開來源、私有 codebase、內部文件、個人筆記都不在裡面。再強的模型也不會「知道你 repo 的內部慣例」。
3. **長尾事實壓縮損失**：訓練資料中出現很多次的常識（如 Python 語法）模型記得清楚、出現一兩次的長尾事實（如某個 obscure library 的某個 function）會被壓縮損失。

RAG 把這三個限制都繞開：retrieval 階段從動態外部 [retrieval source](/llm/knowledge-cards/retrieval-source/)（可即時更新、可放私有資料、可保留長尾完整內容）拉出相關片段、augmentation 階段把這些片段塞進 prompt 當 context。模型不需要「知道」這份知識、只需要「讀懂」當下 prompt 裡的這份知識。

這個結構的根本價值是「把知識從模型權重解耦」。模型負責「語言理解 + 推理」、知識負責「事實儲存 + 動態更新」、兩者各自演化：模型升級不需重建知識庫、知識更新不需重訓模型。具體 retrieval 機制依賴 [embedding model](/llm/knowledge-cards/embedding-model/) 把文字轉成向量、用相似度衡量「相關性」。

## Retrieval 的核心問題：語意相似 vs 字面相似

Retrieval 解的是「給一個 query、找出相關的 document」這個問題、但「相關」有兩種定義：

- **字面相似**（lexical similarity）：query 跟 document 共用多少 keyword。傳統 search engine 用這套（如 Elasticsearch / OpenSearch 的 BM25 算法、以 keyword 出現頻率加權的傳統檢索演算法、不考慮語意）。
- **語意相似**（semantic similarity）：query 跟 document 表達的意思接近、即使共用 keyword 少。Embedding-based retrieval 用這套。

兩種模式的失敗模式恰好互補：

| 場景                               | 字面 retrieval       | 語意 retrieval                   |
| ---------------------------------- | -------------------- | -------------------------------- |
| Query 跟 document 用同樣 keyword   | 找得到（強項）       | 也找得到（多數情況）             |
| Query 用同義詞、document 用另一字  | 找不到               | 找得到（強項）                   |
| 文件用 jargon、query 用通俗描述    | 找不到               | 找得到（強項）                   |
| 兩個 document 字面像但語意不同     | 都找出來（False+）   | 通常能分開（強項）               |
| 兩個 document 語意一樣但字面差很多 | 找不到一個（False-） | 都找出來（強項）                 |
| Embedding 模型不熟悉的 domain      | 不受影響             | 表現崩、retrieval 像隨機（弱項） |

實務上現代 RAG 多半用「hybrid retrieval」：BM25 + embedding 分數加權合併、補單一模式的失敗模式。但理解兩者本質的差異、能解釋為什麼 retrieval 結果有時很準、有時莫名其妙。

語意 retrieval 還帶來一個容易忽略的限制：**embedding 模型本身有訓練分佈**。它在 Wikipedia / Common Crawl 風格的文字上表現好、在你的內部 codebase 風格上表現未必好。Domain shift 是 retrieval 失敗的常見根本原因、不是「embedding 不夠強」、是「embedding 沒見過這類資料」。

## Chunking 的本質取捨

RAG 若把整份文件當 retrieval 單位、document 太長、retrieval 拿到的太粗、實務上要先切成 chunk。Chunk 大小的選擇是 retrieval 設計最關鍵也最容易誤判的決定。

Chunk 太小（如每段 100 token）的失敗模式：

- 每塊資訊不完整、retrieval 拿到的 fragment 無法獨立理解（如「他在第三章提到這個概念」、但「他」「這個概念」需要前文才解得開）。
- 跨 chunk 的語意關聯被切斷、retrieval 拿到一個 chunk 但相關的補充資訊在下個 chunk。
- 同一個概念可能切到多個 chunk、retrieval 拿其中一個是不完整論述。

Chunk 太大（如每段 2000 token）的失敗模式：

- Retrieval 精確度低、一個 chunk 包含多個主題、相似度計算被無關內容稀釋。
- 塞進 prompt 浪費 [token](/llm/knowledge-cards/token/)、context 利用率差。
- 重要訊號可能埋在 chunk 中間、被前後 noise 蓋過。

「resolution vs context loss」是無法兩全的設計問題：細粒度精確但缺脈絡、粗粒度有脈絡但精度差。不同任務有不同最適點：

- 問答任務（答案是短句）：偏細粒度、500 token 左右常見。
- 摘要任務（答案需要長段脈絡）：偏粗粒度、1500-2000 token 常見。
- Code retrieval：以邏輯單位切（function、class）、不是按 token 數切。
- 規格 / 法律文件：按章節結構切、保留 hierarchy。

Chunking 還有兩個常被忽略的設計維度：

- **Overlap**：相鄰 chunk 之間留 10-20% overlap、避免「重要訊號剛好被切斷」。
- **語意邊界 vs 字數邊界**：純按字數切會穿過句子或段落中間；按段落 / heading / 邏輯單位切保留語意完整、但實作複雜。

寫 code 場景的 retrieval（如 Continue.dev 的 `@codebase`、即 IDE 內把整個 codebase 當 retrieval 來源的指令）多半按邏輯單位切 code（function、class、import block）、配合 AST 解析、比純文字 chunking 收益高很多。

## Retrieval 失敗的根本原因

Retrieval 結果不理想時、根本原因通常落在這幾類：

### 語意 gap

Query 跟 document 描述的是同一個東西、但用詞、立場、抽象層級都差很多，這是 [query-document gap](/llm/knowledge-cards/query-document-gap/)。例：query 是「怎麼讓 API 跑快」、document 是「latency optimization techniques」。Embedding 模型訓練得好的話可以對齊、訓練不好或 domain 不熟就 miss。緩解：query rewriting（讓 LLM 把 query 改成更接近 document 的 phrasing）、HyDE（hypothetical document embeddings、用 LLM 生成「假設的答案」、用這個假答案的 embedding 去 retrieval）。

### 超出訓練分佈

Embedding 模型對某個 domain 表現崩（如金融術語、醫療 jargon、特殊 codebase 慣例）。判讀訊號：retrieval 結果看起來「隨機」、語意相關性低。緩解：換 domain-specific embedding 模型、或退回 BM25。

### Chunk 邊界穿過語意單位

正確答案被切到兩個 chunk、retrieval 拿到的只是其中半邊。判讀訊號：模型回答不完整或「我看到 X 但不知道 Y」、檢查發現 Y 在相鄰 chunk。緩解：加 overlap、改用語意邊界 chunking。

### Query 過短缺乏 disambiguation context

Query 太短、模型不知道使用者真正想要什麼（如 query 「python」可以指語言、shell binary、套件、文件章節）。Retrieval 拿到的可能語意完全錯。緩解：在 retrieval 前讓 LLM expand query、加上對話歷史當 context。

### Embedding 跟下游 LLM 訓練分佈不一致

Embedding 模型擅長把「相關」拉近、但「相關」的定義可能跟下游 LLM 「能用」的定義不同。例：embedding 把同義詞拉近、但下游 LLM 需要的是「能完整回答 query 的 document」、不是「跟 query 同義」。判讀訊號：retrieval 看起來合理但回答品質差。緩解：retrieval + re-ranker（用較強模型對 retrieval candidates 再排序）。

這五類失敗各有自己的訊號、根本原因不同、緩解策略也不同。Retrieval 出問題時、先用症狀分類、再對應到根因、比「換更大 embedding 模型」這種反射式修法有效得多。

## Production retrieval pipeline：hybrid + reranker

實務 production RAG 多不只用單一 embedding-based retrieval、而是「[hybrid search](/llm/knowledge-cards/hybrid-search/) + [reranker](/llm/knowledge-cards/reranker/)」兩段式：

```text
User query
   ↓
[Stage 1: Hybrid retrieve top-50]
   ├── BM25（字面）retrieve top-25      ← 抓精確 keyword、識別碼、罕見 entity
   └── Embedding（語意）retrieve top-25  ← 抓同義詞、jargon、語意相似
   ↓ Reciprocal Rank Fusion 合併
   top-50 candidates
   ↓
[Stage 2: Reranker rerank to top-5]
   Cross-encoder 對每對 (query, doc) 算 fine-grained relevance
   ↓
   top-5 給 LLM
```

為什麼兩段式：

| 路線                       | 強項                        | 盲點                                              |
| -------------------------- | --------------------------- | ------------------------------------------------- |
| BM25-only                  | 精確 keyword、識別碼、術語  | 語意相似抓不到（同義詞、不同表述）                |
| Embedding-only             | 語意相似強                  | 罕見 entity、嚴格 keyword 容易漏                  |
| Hybrid（BM25 + embedding） | 互補、覆蓋更廣              | 但 top-50 仍有「相關但不精確」                    |
| Hybrid + reranker          | 兩段式、最終 top-5 精確度高 | 每對 reranker call 慢、需要 cost / latency budget |

何時不需要 reranker：

- 小語料（< 1000 docs）、embedding 已準
- 純 keyword 任務、BM25 已準
- 極低 latency 要求（reranker 加幾百 ms）

主流 reranker：Cohere Rerank 3（SaaS）、Jina Reranker v2（OSS）、BGE Reranker（OSS、中文友善）、Voyage rerank-2。詳細選型見 [reranker 卡](/llm/knowledge-cards/reranker/)。

## Chunking 策略對比

[chunking 卡](/llm/knowledge-cards/chunking/) 講概念、實務有五種主流策略：

| 策略                      | 機制                                       | 適合                             | 失敗模式                       |
| ------------------------- | ------------------------------------------ | -------------------------------- | ------------------------------ |
| Fixed-size                | 按 token 數固定切（如每 512 token）        | 通用 baseline、簡單              | 切壞句子 / 段落邊界、語意斷裂  |
| Recursive                 | 按分隔符遞迴切（先段落、再句、再固定大小） | 通用文字、保留段落結構           | 仍可能切壞表格 / 程式碼        |
| Markdown header           | 按 markdown 標題切（H1/H2/H3）             | 文檔、技術文章、有明確 structure | 標題層級不一致時破             |
| Code-aware（tree-sitter） | 按 AST 切（function / class 邊界）         | 程式碼 retrieval                 | 跨檔案邏輯抓不到               |
| Semantic                  | 用 embedding 判段落語意邊界、切在語意斷點  | 知識文章、長 narrative           | 慢、需要 pre-process embedding |

判讀流程：

```text
內容類型？
├── 純文字 / 文章       → Recursive 或 Semantic
├── Markdown 文檔       → Markdown header（fallback recursive）
├── 程式碼              → Code-aware（tree-sitter）
├── 混合（文章 + code） → Markdown header 主、code block 用 tree-sitter
└── PDF                 → 先轉 Markdown 再用 Markdown header

Chunk 大小？
├── 一般 RAG            → 512-1024 token、overlap 50-100 token
├── 短回答 / 精確匹配  → 256-512 token、更精確
└── 整段理解 / 長 narrative → 1024-2048 token、配合 long context model
```

實務常見錯誤：

1. **拿 raw PDF 直接 chunking**：PDF 結構亂、應該先轉 markdown
2. **過大 chunk 套小 context embedding**：bge-large context limit 512、塞 2048 chunk 直接截斷
3. **不加 overlap**：句子被切斷、retrieval 漏前後文
4. **混合語料用同樣 chunking**：technical doc + casual blog + code 一視同仁、品質都差

## RAG vs Fine-tuning vs Long Context

「讓模型知道新東西」有三條路、解的問題層級不同：

| 路線         | 機制                              | 適合場景                              | 不適合場景                         |
| ------------ | --------------------------------- | ------------------------------------- | ---------------------------------- |
| RAG          | 動態外掛知識、prompt 時 retrieval | 動態更新、知識量大、需要 traceable    | 需要 holistic 理解、知識高度結構化 |
| Fine-tuning  | 改變模型權重、教新行為 / 領域知識 | 風格 / 領域特化、有專屬 training data | 知識常變、訓練資料少               |
| Long context | 整份知識直接塞 prompt             | 知識量小（< context 上限）、單次任務  | 知識重複用（每次塞 cost 高）       |

三者不互斥、實際應用常組合使用：fine-tune 模型懂 domain jargon、RAG 拉動態知識、long context 在單一任務塞完整脈絡。

判讀「該用哪一條」的核心問題：

- 知識會不會變？常變 → RAG。穩定 → fine-tune 或 long context。
- 知識量多大？小（< 100K tokens、塞得進 [context window](/llm/knowledge-cards/context-window/)）→ long context。大 → RAG。
- 需要 traceable（知道答案來源）？是 → RAG（每個 chunk 有 source）。否 → fine-tune 也可。
- 是行為 / 風格還是事實？行為 → fine-tune（教模型「該怎麼回應」）。事實 → RAG（教模型「該知道什麼」）。

寫 code 場景：codebase 變得快、量大、需要 traceable（要知道參考的是哪個 file）——RAG 是預設選擇。Fine-tune 在「想讓模型懂特定 codebase 風格 / 慣例」時補上、但在 codebase 變動頻繁的多數場景成本壓過收益；少數穩定大型 codebase 且風格規範強的情境（如金融 / 醫療 SDK）才值得評估 fine-tune。

## 何時不適合 RAG

RAG 適用面有邊界、下列情境改用其他方案更划算：

- **需要 holistic 理解整份文件**：如改寫整篇文章的風格、跨段邏輯重組。Retrieval 拿到的是片段、看不到整體。改用 long context 把整份塞進 prompt、或先讓 LLM summarize 再對 summary 操作。
- **知識是高度結構化資料**：如使用者資料庫、產品目錄。直接用 SQL query 比 embedding retrieval 精確得多。RAG 變成繞遠路。
- **知識量小、每次都會用到**：如系統 prompt 的角色設定、不變的規則。直接寫進 system prompt 比每次 retrieval 簡單。
- **[Retrieval cost](/llm/knowledge-cards/retrieval-cost/) 高於 long context**：知識量壓過 context 但壓力不大（如 50K tokens）、retrieval pipeline 維護成本可能高於直接塞長 context。值不值得做 RAG 看 query 頻率：偶爾用就 long context、高頻用才值得建 retrieval。
- **Latency 敏感場景**：RAG 加一輪 retrieval、[TTFT](/llm/knowledge-cards/ttft/) 變長。即時補完場景可能受不了。

判讀「該不該做 RAG」的反射：先問「不做 RAG 會怎樣」、再評估 RAG 的維護成本。RAG 不是免費的——需要 ingestion pipeline、embedding 服務、vector database、retrieval logic、re-ranker、評估系統。判讀 overengineering 的訊號：查詢量 < 100/day、文件 < 1000 份、變動頻率 < 月一次、這類規模通常 long context + 簡單檔案讀取已足夠；超過這個量級才值得建完整 RAG stack。

## 何時過時 / 何時不過時

**不會過時的部分**：

- Retrieval + augmentation 的二段式結構：retrieve 找相關內容、augment 塞進 prompt。這個 framing 跟具體實作無關。
- 語意 vs 字面相似的差異跟互補性。
- Chunking 的 resolution vs context loss 取捨。
- 五類 retrieval 失敗模式的分類。
- RAG / fine-tuning / long context 三條路線的判讀框架。

**會變的部分**：

- 具體 embedding 模型（nomic-embed、bge、mxbai 等會持續更新）。
- Vector database 選型（Pinecone / Weaviate / Chroma / pgvector 等市場格局會變）。
- Framework API（LangChain / LlamaIndex 的具體呼叫方式半年一變）。
- 最佳 chunk size 數字（隨 embedding 模型跟 LLM context 能力演化）。
- Hybrid retrieval / re-ranker 的具體實作（會持續優化）。

當這篇文章「過時」的時候、過時的是參考數字跟工具選型；retrieval 本質、失敗模式、跟其他路線的取捨判讀仍會成立。看到新 RAG 工具時、回到本章的 framing：它解的是哪類問題、它的 chunking 策略是什麼、它如何處理五類失敗模式——能很快判斷它解的問題跟你的場景是否對齊。

## 小結

RAG 是「retrieval + augmentation」的二段式結構、把 LLM 的知識限制（cutoff、私有資料、長尾壓縮損失）從根本繞開。Retrieval 階段是設計重點：語意 vs 字面相似的互補、chunking 的 resolution vs context 取捨、五類失敗模式各自的根因。RAG / fine-tuning / long context 三條路線的選擇取決於知識變動頻率、量級、結構化程度。本章預設「有 backend」、沒 backend 的場景（個人 blog、docs site 加 RAG）的 deployment 取捨見 [4.16 靜態 / serverless RAG deployment](/llm/04-applications/static-and-serverless-rag-deployment/)。

下一章：[4.2 RAG 檢索增強](/llm/04-applications/rag-retrieval-enhancements/)、看 vanilla RAG 不夠用時的下一層工具箱（query rewriting / HyDE / multi-step / [context packing](/llm/knowledge-cards/context-packing/)）。把 LLM 從讀資料延伸到對外部世界做事見 [4.3 Tool use 原理](/llm/04-applications/tool-use-principles/)。Retrieval 把外部內容引入 prompt 本身就是攻擊面（同個機制讓 codebase 內容、外部文件、剪貼簿都能間接影響模型輸出）、IDE 場景的 prompt injection 判讀見 [6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)。
