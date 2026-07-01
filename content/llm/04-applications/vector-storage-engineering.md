---
title: "4.22 RAG storage 工程：從 pickle 到 vector database 的升級判讀"
date: 2026-07-01
description: "RAG storage backend 選型：規模到哪個階段該從 in-memory 升級到 vector DB、dependency chain 如何收窄選項"
tags: ["llm", "applications", "rag", "vector-database", "embedding", "storage"]
weight: 22
---

做完 RAG proof-of-concept 後最常見的問題是「現在的 in-memory 方案什麼時候該換成 vector database」。RAG pipeline 的儲存方案是**工程選擇、不是概念要件**。[4.1 RAG 原理](/llm/04-applications/rag-principles/)定義的 retrieval + augmentation 二段式結構，跟 embedding 存在 pickle、flat file、SQLite、還是 Pinecone 無關 — 只要能「給一個 query vector，找到最相似的 chunk vectors」，retrieval 這一段就成立。

本章整理 storage layer 的工程設計空間：什麼規模用什麼儲存、什麼訊號觸發升級、index 怎麼建怎麼更新、schema 怎麼設計、dependency chain 怎麼影響選型。全篇以一個約 200 篇 markdown、Go 工具鏈的個人技術 blog 作為 running example（從 [pickle demo](/llm/01-local-llm-services/hands-on/rag-demo/) 升級到 production 工具的過程）；Go-specific 的約束見「工程約束」段，Python 專案的路徑在各階段標示。

## 本章目標

本章涵蓋：

1. RAG pipeline 的四個可替換層、判斷當前瓶頸落在哪一層。
2. Corpus 規模跟使用模式對應的 storage backend 選擇。
3. Index 的 build / update / rebuild 生命週期設計。
4. ANN index 策略（HNSW / IVF / brute-force）的適用邊界。
5. Storage 選型的 dependency 約束（語言生態、build chain、環境管理）。

## RAG pipeline 的四個可替換層

RAG 不是一個 monolithic 系統。從 query 進來到 augmented prompt 送進 LLM，經過四個獨立可替換的層：

| 層                  | 責任                                | 可替換選項範例                                     |
| ------------------- | ----------------------------------- | -------------------------------------------------- |
| Chunking strategy   | 把 corpus 切成 retrieval 單位       | fixed-size / recursive / heading-aware / AST-based |
| Embedding model     | 把 chunk text 轉成向量              | nomic-embed-text / bge-large / jina-v3             |
| **Storage backend** | 存向量 + metadata、支援相似度查詢   | pickle / flat file / FAISS / SQLite-vec / Pinecone |
| Retrieval algorithm | 對 query vector 找 top-K 相似 chunk | brute-force cosine / HNSW / IVF / hybrid + rerank  |

四層各自演化、各自有不同的升級時機。Chunking 跟 embedding model 影響 retrieval **品質**（找到的東西對不對）；storage backend 跟 retrieval algorithm 影響 retrieval **效能**（找的速度跟規模上限）。

常見的認知混淆是把「RAG」跟「vector database」綁在一起。這個綁定在 production 規模可能合理（10M chunks 不用 vector DB 很難做），但在小規模場景會導致過度工程 — 1500 個 chunks 用 Pinecone 就像用 PostgreSQL 存 10 筆 config。

## Storage backend 的演化階梯

Storage backend 的選擇是**規模驅動**的工程決策。每個階段都能做 RAG，差別在效能、持久性、query 能力。以下規模閾值基於 768 維 embedding、單機常見配置的經驗判斷，切點依向量維度與硬體規格移動；實測數字（如 20 chunks/sec）另行標示：

### 階段一：In-memory（pickle / Python list）

把所有 chunk embeddings 載入記憶體，brute-force 算 cosine similarity。

```text
適用規模：< 10K chunks
延遲：< 10ms（1500 chunks × 768 dim ≈ 4.5MB，全在 L3 cache）
持久性：pickle 檔、每次啟動重載
優點：零 dependency、程式碼 < 50 行、debug 容易
限制：記憶體受限、無 metadata filter、無 incremental update
```

本 blog 的 [rag-demo](/llm/01-local-llm-services/hands-on/rag-demo/) 就在這個階段：71 篇 markdown、463 chunks、pickle 儲存、22 秒索引、query < 10ms。概念驗證完全夠用。

### 階段二：Flat file（binary embedding store）

把 embeddings 存成 binary 格式（而非 Python pickle），配 JSON metadata index。跟階段一的差異是 **language-agnostic persistence** — 不綁定 Python 的 pickle 格式、Go / Rust / Node 都能讀。

```text
適用規模：< 10K chunks
延遲：< 10ms（同樣 brute-force）
持久性：binary file + metadata JSON、可 rebuild
優點：跨語言、單檔案部署、不需要 DB server
限制：brute-force O(n)、metadata filter 靠程式碼、schema 演化需 rebuild（換 embedding 模型要重建整個 index）、無 transaction 保護（binary 損毀靠 rebuild 復原）
```

Running example 的 blog 選了這個方案。驅動選擇的是**工具鏈約束**：該 blog 的核心工具是 Go（單 binary 分發的 lint / fmt 工具），用 pickle 就綁定 Python runtime、其他維護者 clone 後多一步環境設定（同規模下效能無差異）。Binary flat file 讓 Go 工具直接讀寫、維持單 binary 分發。Python 專案留在 pickle 完全合理，規模到 10K 再跳階段三 FAISS 更自然。

### 階段三：Embedded library（FAISS / HNSWLib / Annoy）

引入 ANN（Approximate Nearest Neighbor）index，查詢從 O(n) 變成 O(log n)。

```text
適用規模：10K - 100K chunks
延遲：< 5ms（HNSW sublinear）
持久性：index 檔案、可 rebuild
優點：不需要 server、嵌入應用 process
限制：需要安裝 library（FAISS 有平台相依的 wheel）、index build 較慢
```

升級訊號：brute-force latency 開始感覺到（> 50ms）、或 corpus 大到記憶體載入太慢。1M chunks × 768 dim × 4 bytes = 3GB，載入開始有感。

### 階段三½：Piggyback 既有 DB（pgvector / Redis vector）

已有 PostgreSQL 或 Redis 的專案有一條跳板路徑：直接在既有 DB 加向量能力、不引入新 server。

```text
適用規模：10K - 1M chunks（pgvector）、10K - 500K（Redis vector）
延遲：< 10ms（HNSW、同 DB process）
持久性：DB 管理、有 transaction / WAL / backup
優點：不增 server、SQL metadata filter 原生支援、既有維運流程直接沿用
限制：DB 本身要夠大（向量索引佔額外記憶體）、效能跟 DB 負載共享
```

升級訊號：已有 Postgres / Redis、需要 metadata filtering、但不想維運獨立 vector DB server。pgvector 讓「有 SQL 能力 + 有向量搜尋」在同一個 DB 完成；Redis vector（RediSearch）適合已有 Redis 且延遲敏感的場景。

這條路徑跟階段四的差異：階段四（Qdrant / Weaviate）是專用 vector DB、向量搜尋效能更高、但多一個 server 維運。Piggyback 路徑犧牲一些向量搜尋效能、換來零新增 server 的維運簡化。選擇取決於「向量搜尋是核心能力（階段四）、還是輔助功能（piggyback）」。

### 階段四：Self-hosted vector database（Qdrant / Weaviate / Milvus）

獨立 server process，專精向量搜尋，支援 metadata filtering、incremental update、backup、replication。

```text
適用規模：100K - 10M chunks
延遲：< 10ms（HNSW + 網路 overhead）
持久性：server 管理、disk-based
優點：metadata filter（SQL-like）、REST/gRPC API、可水平擴展
限制：需要維運 server、佔用資源、增加系統複雜度
```

升級訊號：需要 metadata filtering（「只搜 report/ 下的卡片」且頻率高）、需要多 process 並發 query、需要 incremental update 而非全量 rebuild。

典型場景是十人以上的團隊共用 RAG 知識庫：多人同時 query、文件隨 sprint 密集更新、需要按 project / team / access level 做 metadata filter。單人或小團隊的 side project 通常停在階段二或三就夠。回退路徑是「關掉 server、退回 embedded library」— 向量跟 metadata 仍在、只是失去 incremental update 跟 REST API。

### 階段五：Hosted SaaS（Pinecone / Weaviate Cloud / Qdrant Cloud）

由 vendor 管理的 vector database，免維運。

```text
適用規模：> 10M chunks、或不想維運
延遲：10-50ms（加上網路 round trip）
持久性：vendor 管理
優點：免維運、自動擴展、SLA
限制：cost、vendor lock-in、資料離開本地
```

升級訊號：corpus 超過單機記憶體（10M+ chunks 的 HNSW index 含 graph overhead 可達數十 GB）、或團隊沒有 infra 維運能力。

典型場景是跨國 SaaS 產品的 knowledge base：文件數百萬、多語言、需要 geo-distributed 部署。此規模下 self-hosted 的維運成本（on-call、capacity planning、backup）可能高於 SaaS 訂閱。風險是 vendor lock-in — 切換 vendor 要 re-index 全量資料、migration 成本跟 corpus 大小成正比。回退計畫是保留 ingest pipeline 的 vendor-agnostic 部分（chunking + embedding），只替換 storage layer。

### 階梯的核心判讀

每階段的升級都帶來新的 dependency 跟維護成本。判讀「該不該升級」看三個訊號：

1. **目前這個階段有具體痛點嗎？** 沒有就不升級。
2. **升級解的是效能瓶頸還是功能缺口？** 效能瓶頸先量測再決定；功能缺口（如 metadata filter）看使用頻率。
3. **升級引入的 dependency 成本能接受嗎？** 單人 blog 加一個 server process 的維護成本跟十人團隊不同。

常見路徑速查：Python 小型 side project 留在 pickle（階段一），規模到 10K 再上 FAISS（階段三）；Go 專案跳階段二（flat file）避免 Python dependency；已有 Postgres 的專案直接評估 pgvector（階段三½）；已有 Docker 的團隊直接評估階段四（vector DB container）。

常見誤解：「FAISS 跟 Pinecone 選哪個」— 兩者差在規模量級（FAISS 是嵌入式 library、適合 < 100K；Pinecone 是 hosted SaaS、適合 > 10M 或免維運），不是同層級的互斥選項。

## ANN index 策略

Storage backend 到了階段三以上，需要選 ANN（Approximate Nearest Neighbor）index 策略。[Vector database 卡](/llm/knowledge-cards/vector-database/)列了三種主流演算法，本段補充工程判讀。

### Brute-force（exhaustive search）

對 query vector 跟所有 stored vectors 算 cosine similarity，取 top-K。

```text
時間複雜度：O(n × d)（n = chunk 數、d = 向量維度）
精確度：100%（exact nearest neighbor）
記憶體：n × d × 4 bytes（float32）
適用：< 10K chunks
```

1500 chunks × 768 dim 的 brute-force，現代 CPU 做一次 cosine similarity sweep 大約 1-5ms。在這個規模，HNSW 的建 index 時間（秒級）反而比它省下的查詢時間（毫秒級）長。

### HNSW（Hierarchical Navigable Small World）

建多層隨機圖，查詢時從稀疏高層往密集低層跳，sublinear 找到近似最近鄰。

```text
時間複雜度：O(log n × d)
精確度：95-99%（approximate、可調 ef_search 參數換精度）
記憶體：n × d × 4 bytes + graph overhead（通常 1.2-1.5x）
Build 時間：O(n × log n)、比 brute-force 慢
適用：10K - 10M chunks、記憶體充足
```

HNSW 是目前 vector DB 的主流 index。工程取捨在兩個參數：`ef_construction`（build 精度、越高越慢但 graph 品質越好）跟 `ef_search`（query 精度、越高越慢但 recall 越高）。多數 vector DB 的預設值已經針對「recall > 95%」調過。

### IVF（Inverted File Index）

先把向量 K-means 分群，query 時只搜最近的幾個群。

```text
時間複雜度：O(n/k × d)（k = 群數、nprobe = 搜幾個群）
精確度：依 nprobe、通常 90-98%
記憶體：可以 disk-based（比 HNSW 省）
Build 時間：K-means 收斂需要時間
適用：> 1M chunks、記憶體受限、可接受較低 recall
```

IVF 在超大規模（10M+）的 disk-based 場景有優勢，實務常配 product quantization（PQ）壓縮向量換記憶體。PQ / scalar quantization 跟 index 演算法（HNSW / IVF）正交 — 是記憶體受限時的壓縮手段，可疊加在任一 index 上。消費級場景通常不需要 quantization。

### 判讀流程

```text
Corpus 規模？
├── < 10K chunks   → Brute-force（此規模無需再評估）
├── 10K - 100K     → HNSW（如果記憶體夠）或 brute-force（如果 latency 可接受）
├── 100K - 10M     → HNSW（主流）
└── > 10M          → IVF 或 HNSW + sharding
```

規模是第一軸。兩個修正軸在同規模下改變選擇：

- **Dependency constraint**（見「工程約束」段）：規模小但工具鏈排除某些 storage（如 Go 專案排除 CGo dependency）→ 從可行選項中選。
- **Metadata filter 需求**：規模小但高頻需要按 section / tag 過濾 → 跳過 embedded library、直接評估 vector DB 或 code filter。

一個常見的過度工程信號：corpus 只有幾千筆但花時間調 HNSW 的 `ef_construction`。即使 HNSW 的 build 成本可以攤提到每次查詢（build 一次、查很多次），此規模的單次查詢絕對延遲（1-5ms brute-force）已在感知閾值下，優化的絕對收益趨近零。

## Index 生命週期

Index 的 build / update / rebuild 流程影響日常維護成本。

### Full rebuild

每次從 corpus 全量重建 index：walk 所有檔案 → chunk → embed → store。

```text
適用：corpus 小（< 10K chunks）、更新頻率低（每週幾次）
優點：邏輯最簡單、index 跟 corpus 保證一致
成本：1500 chunks × embedding API call ≈ 60-90 秒（本地 Ollama、sequential；batch/async 可縮短）
```

本 blog 選 full rebuild：200 篇 markdown 全量 ingest 在本地 Ollama 約 60-90 秒（sequential embedding、約 20 chunks/sec）。每天變動 0-3 篇，rebuild 頻率跟 `git push` 對齊就夠。

### Incremental update

只處理有變動的檔案：偵測 diff → 刪除舊 chunks → 重新 chunk + embed 變動檔 → 插入新 chunks。

```text
適用：corpus 大（> 10K chunks）、更新頻繁
優點：只處理 delta、省 embedding API cost
複雜度：需要 chunk ID 穩定（file path + chunk offset）、刪除 orphan
```

Incremental update 的工程難點是 **chunk ID 穩定性**。如果 chunking 策略對同一個檔案的切法會因為上游內容變動而改變（例如段落感知 chunking，加一段就改變後續所有 chunk 邊界），「只更新變動的 chunk」就需要 diff 整個 chunk 序列，邏輯接近全量重建。

判讀「該不該做 incremental」：

- Embedding 是 cost 瓶頸嗎？本地 Ollama 的 embedding 幾乎免費（約 50ms/chunk、sequential）；cloud API（OpenAI text-embedding-3-small 約 $0.02/1M tokens、Cohere 類似）按 token 計費、corpus 大時差異顯著。
- 全量 rebuild 的時間能接受嗎？1500 chunks 在本地約 60-90 秒可以接受；15 萬 chunks 約 2 小時可能不行。
- 能容忍短暫不一致嗎？Full rebuild 期間 index 可能是舊版；incremental update 隨改隨更新。

### Rebuild trigger

不管 full 或 incremental，都要決定「什麼觸發 rebuild」：

| Trigger 類型 | 做法                                          | 適合           |
| ------------ | --------------------------------------------- | -------------- |
| 手動         | `blogsearch ingest` 手動跑                    | 個人工具       |
| Git hook     | pre-push 或 post-commit 自動 rebuild          | 小團隊         |
| CI/CD        | push to main 後 CI job 跑 ingest              | 多人協作       |
| File watcher | inotify / fsevents 偵測 content/ 變動自動更新 | 開發中即時回饋 |

Trigger 跟團隊協作模式對齊：單人用手動；多人但 review cycle 長（每天幾次 push）用 Git hook 或 CI/CD；開發中密集寫作想即時看 retrieval 結果用 file watcher。Git hook 跟 CI/CD 的差異在 rebuild 跑在本地（hook）還是 server（CI）— 本地 rebuild 快（< 2 分鐘）就用 hook、慢就推到 CI 避免 push 卡住。

本 blog 目前用手動 trigger — 維護者在寫新文章、需要查相關內容時跑 `blogsearch ingest`，日常使用頻率不高、不需要即時同步。

## Schema 設計

每個 chunk 存的不只向量。至少有三類資料需要管理：

```text
chunk = {
    vector:   float32[768],       // embedding
    text:     string,             // 原始文字（generation 用）
    metadata: {                   // filtering + 溯源
        source:    string,        // 來源檔案路徑
        section:   string,        // 所屬 section（llm/ / backend/ / report/）
        title:     string,        // 文章標題
        date:      string,        // 文章日期
        tags:      []string,      // 文章 tags
        chunk_idx: int,           // 該檔案內的第幾個 chunk
    }
}
```

### Metadata filter 的設計取捨

Metadata filter 是「在向量相似度之外加條件」：例如「只搜 report/ 下的卡片」「只搜 2026 年之後的文章」。

兩種實作路線：

**Code filter**：先做 brute-force / ANN 取 top-N（N 大於最終需要的 K），再用程式碼 filter metadata，取 top-K。

```text
優點：不需要 DB、flat file 就能做
限制：filter 比例高時（如 90% 被 filter 掉）需要取很大的 N
適用：filter 條件少、filter 比例低（< 50%）
```

**DB filter**：在 vector DB 的 query 語法中直接加 metadata condition（如 Qdrant 的 `must` filter）。

```text
優點：filter 在 index 層執行、效率高
限制：需要 vector DB、schema 要先定好
適用：filter 條件多、filter 比例高、query 頻繁
```

本 blog 選 code filter：section 只有幾個值（llm / backend / report / work-log），filter 比例低，brute-force top-20 再 filter 到 top-5 就夠。

### Hybrid search 的 schema 考量

[4.1 RAG 原理](/llm/04-applications/rag-principles/)介紹了 [hybrid search](/llm/knowledge-cards/hybrid-search/)（BM25 關鍵字精確匹配 + embedding 語意相似度的加權合併），在 storage 層的 schema 影響是：需要同時存**原始文字**（給 BM25）跟**向量**（給 embedding search）。

- In-memory / flat file：BM25 自己實作（或用 library），原始文字本來就存了。
- Vector DB：多數支援 hybrid search（Qdrant 有 full-text index、Weaviate 有 BM25 + vector 合併查詢）。
- SQLite-vec + FTS5：SQLite 原生支援 full-text search（FTS5），配 sqlite-vec 可以在同一個 DB 做 hybrid search。

判讀「要不要 hybrid」：先只用 embedding search，retrieval 品質不夠再加 BM25。多數場景 embedding-only 已經夠用；keyword 精確匹配需求高的場景（如搜特定 error message、RFC 編號）才需要 BM25 補。

## 工程約束：dependency chain 與 build system

Storage 選型不只看功能跟效能，還受**工程約束**影響。以下用 Go 專案示範 dependency constraint 的思考方式；Python / Docker / 前端專案的 constraint 不同、結論見「不同專案的 constraint 不同」段。

### Case study：Go 專案為什麼不選 SQLite-vec

SQLite-vec 是 SQLite 的 C extension，提供向量搜尋能力。功能上完全符合需求。但在 Go 生態裡，CGo（Go 呼叫 C 程式碼的橋接機制）引入額外代價：

| SQLite Go binding                 | 能用 sqlite-vec？ | 代價                                          |
| --------------------------------- | ----------------- | --------------------------------------------- |
| `modernc.org/sqlite`（純 Go）     | 不能              | 純 Go 重寫的 SQLite 不支援載入 C extension    |
| `mattn/go-sqlite3`（CGo binding） | 能                | 需要 C compiler、交叉編譯困難、build 時間增加 |

選 `mattn/go-sqlite3` 意味著：

- 其他維護者 clone 後需要裝 C compiler（macOS 要 Xcode CLI tools、Linux 要 gcc）
- CI/CD 需要配 CGo 環境
- 單 binary 分發的優勢消失（動態連結 libc）

這些代價在大團隊可能值得，但對一個個人 blog 的工具來說，dependency chain 的複雜度超過功能收益。

### 判讀 dependency 約束的反射

每個 storage 選項都帶一條 dependency chain。評估時要問：

1. **新維護者 clone 後要裝什麼？** pip install / go build / docker pull / apt install？
2. **CI 要加什麼？** C compiler / Python runtime / Docker image？
3. **哪些平台要支援？** macOS / Linux / Windows？交叉編譯需求？
4. **runtime dependency 還是 build-time dependency？** Runtime（要 server 跑著）的維護成本遠高於 build-time（build 完就不需要了）。

本 blog 的 constraint 是：Go 單 binary、clone 後 `go build` 即可、不需要外部 server。這個 constraint 排除了 CGo dependency 跟任何 server-based 方案，把選項收窄到 flat file。

### 不同專案的 constraint 不同

這個 constraint 是本 blog 的特定情境。其他專案的 constraint 可能完全不同：

- Python 生態的專案：pip install 是標準流程，但 FAISS 的 CPU/GPU wheel 有平台相依（M1 Mac 需要 `faiss-cpu` 特定版本、glibc 版本影響 Linux wheel），不是完全零 constraint。
- 已有 Docker 的專案：加一個 Qdrant container 看似 `docker-compose.yml` 多三行，但要考慮 image 體積（數百 MB）、記憶體分配、冷啟動時間、以及 CI 環境是否支援 Docker-in-Docker。
- 前端專案：WebAssembly 版 HNSW 可行但受 bundle size 跟瀏覽器記憶體上限約束，跟 backend storage 的 constraint 型態完全不同。

Storage 選型沒有「最佳方案」— 只有在特定 constraint 下的最適方案。

## 何時過時 / 何時不過時

**不會過時的部分**：

- RAG pipeline 的四層可替換結構。
- Storage 升級的判讀訊號（規模驅動、痛點驅動、不是技術驅動）。
- Index 生命週期的 full rebuild vs incremental update 取捨。
- Dependency chain 作為選型約束的思考框架。
- ANN 策略的複雜度分析（brute-force O(n) vs HNSW O(log n) vs IVF O(n/k)）。

**會變的部分**：

- 具體 vector DB 的市場格局（Pinecone / Qdrant / Weaviate 的功能差異會持續變動）。
- ANN library 的實作效能（新演算法可能比 HNSW 更好）。
- 語言生態的 binding 成熟度（Go 的 SQLite-vec 純 Go binding 可能出現）。
- 具體規模閾值（隨硬體進步、「brute-force 可行」的上限會提高）。

## 跟其他章節的關係

| 章節                                                                    | 跟本章的分工                                                         |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [4.1 RAG 原理](/llm/04-applications/rag-principles/)                    | 定義 retrieval + augmentation 本質、本章處理 storage layer           |
| [4.2 RAG 檢索增強](/llm/04-applications/rag-retrieval-enhancements/)    | 處理 retrieval algorithm 層的增強、本章處理 storage 層               |
| [4.12 Embedding model](/llm/04-applications/embedding-model-internals/) | 處理向量怎麼生成（含實務選型 constraint 優先序）、本章處理向量怎麼存 |
| [4.10 衍生產物管理](/llm/04-applications/artifact-management/)          | Index 是 derived artifact、不進 git、用 manifest 描述                |
| [Vector database 卡](/llm/knowledge-cards/vector-database/)             | 概念定義與 ANN 演算法摘要、本章補工程判讀                            |

## 下一步

本章整理的是跨場景的 storage 工程原則。本 blog 基於這些原則選了「Go + flat file + brute-force」方案，具體實作（CJK chunking 實測、跟 mdtools 的整合過程）將作為 hands-on 實作篇補入 [04-applications/hands-on](/llm/04-applications/hands-on/)。

想看 retrieval 品質不夠時的增強手段（query rewriting / HyDE / multi-step），回到 [4.2 RAG 檢索增強](/llm/04-applications/rag-retrieval-enhancements/)。想看 embedding 模型怎麼選（含工程 constraint 如何先砍選項再比品質）、怎麼判讀 MTEB 分數，回到 [4.12 Embedding model 內部](/llm/04-applications/embedding-model-internals/)。
