---
title: "Case Study：Blog 語意搜尋從 pickle 到 production"
date: 2026-07-01
description: "為 CLI 或個人工具選 RAG storage backend、或原始選型理由被 benchmark 推翻但結論不變時，如何區分結論、理由與前提"
tags: ["llm", "hands-on", "rag", "vector-database", "benchmark", "storage"]
weight: 2
---

本案例記錄一個技術 blog（2,738 篇 markdown、24,216 chunks）的語意搜尋工具從 demo 到 production 的完整過程。每段標出對應 [4.22 RAG storage 工程](/llm/04-applications/vector-storage-engineering/) 的哪個判讀步驟，讓讀者看到原理章的框架怎麼落到具體決策。

> **實測日期**：2026-07-01
> **環境**：macOS Apple Silicon、Ollama 0.7.x、`nomic-embed-text`（768 維）
> **Corpus**：`content/` 全量 2,738 個 markdown 檔、24,216 chunks
> **前置 demo**：[rag-demo](/llm/01-local-llm-services/hands-on/rag-demo/)（pickle、463 chunks）

### 讀法建議

本案例用 Go 重寫了 RAG storage 層，Go 實作細節佔不少篇幅。依你的背景選讀法：

- **Python 開發者、想選自己專案的 storage 方案**：先跳到「通用可複製流程」（語言無關的五步驟）→「四方案 benchmark」→「二次選型評估」（結論/理由/前提三層框架），這三段跨語言可遷移。Go 實作段（架構、效能優化）可 skim。
- **Go 開發者、想做類似工具**：從頭讀，每段都跟你相關。
- **只想看選型框架、不管實作**：直接跳「二次選型評估」。

## 從 demo 到 production 的重寫動機

[rag-demo](/llm/01-local-llm-services/hands-on/rag-demo/) 用 Python pickle 跑通了 RAG 概念驗證：71 篇 → 463 chunks → pickle 儲存 → cosine retrieval → Ollama 生成。概念層完全正確（4.1 的 retrieval + augmentation 骨架），但作為這個 blog 的日常工具有三個**專案特有的**限制：

1. **工具鏈語言不同**：blog 的核心工具是 Go（lint / fmt / cards），加 Python dependency 讓其他維護者 clone 後多一步環境設定。Python 專案不會有這個問題 — pickle 綁 Python 對 Python 專案是優點而非缺點。
2. **只索引部分 corpus**：rag-demo 只跑 `content/llm/`（71 篇），blog 全量有 2,738 篇、24 個 section。
3. **Demo 定位**：ingest.py / query.py 是教學程式碼，不是維護工具（沒有 status、沒有 section filter）。

這是一次**完整重寫**、不是漸進升級 — rag-demo 的 Python 程式碼不會被修改或遷移，而是用 Go 重新實作相同的 RAG pipeline（chunk → embed → store → search）、保留相同的概念架構。rag-demo 作為教學 demo 繼續存在。

升級目標：一個跟 `mdtools` 同級的 Go CLI 工具，能對全量 content 做語意搜尋，其他維護者 clone 後 `go build` 即可用。完整原始碼在 `scripts/blogsearch/`。

## 選型過程（對應 4.22 演化階梯 + 工程約束）

### 第一軸：規模判讀

全量 content 產生 24,216 chunks（原本估計 ~1,500）。按 4.22 判讀樹，24K 落在「10K-100K → HNSW 或 brute-force」區間。預估 vs 實際的 16 倍落差揭露一個教訓：**估計 chunk 數不能用篇數乘以常數**，要看每篇的實際長度跟 chunking 策略。

### 第二軸：工程約束（本專案特有）

以下四個 constraint 反映**這個 blog 專案的偏好**、不是通用判準。換一組 constraint 會篩出完全不同的方案 — Python 專案不會有「Go 單 binary」constraint、已有 Docker 的團隊不會排斥外部 server。讀者套用時應先列出自己專案的 constraint、不是照搬這張表。

| Constraint      | 砍掉什麼                                    |
| --------------- | ------------------------------------------- |
| Go 單 binary    | Python-only 方案（pickle / FAISS）          |
| 不要 CGo        | sqlite-vec（需要 `mattn/go-sqlite3`）       |
| 不要外部 server | Qdrant / Weaviate / Pinecone                |
| Ollama 原生     | OpenAI / Cohere embedding（多一個 API key） |

剩餘選項：**Go + flat file + brute-force**。

### 第三軸：延遲容忍

CLI 工具、每天用幾次、不是 API server。< 500ms 可接受。

結論：選階段二（flat file），brute-force cosine。

## 實作架構

```text
scripts/blogsearch/
├── main.go                     # CLI: ingest / query / status
├── cmd/
│   ├── ingest.go               # walk content/ → chunk → embed → store
│   ├── query.go                # load → embed query → cosine top-K → lazy load text
│   └── status.go               # index stats
└── internal/
    ├── chunk/chunk.go           # paragraph-aware markdown chunking
    ├── embed/embed.go           # Ollama HTTP API wrapper
    ├── search/search.go         # brute-force cosine similarity
    └── store/store.go           # 三檔案 binary store
```

### 日常使用

```bash
# 語意搜尋
./bin/blogsearch query "retry 策略"

# 只搜特定 section
./bin/blogsearch query -section backend "connection pool 設定"

# 查 index 狀態
./bin/blogsearch status
```

### Storage 格式（三檔案分離）

```text
.blogsearch/
├── vectors.bin    # float32 binary（70.9 MB）— bulk read + unsafe.Slice 零拷貝
├── meta.json      # compact metadata 不含 text（7.3 MB）
└── texts.bin      # length-prefixed chunk text（19.2 MB）— top-K 才 lazy load
```

分離 text 的設計理由：query 時只需要 vectors + metadata 做 cosine search（78 MB），top-K 結果才從 texts.bin 按 offset 讀取 5 筆 text。省掉 19 MB 的 JSON 解析。

## 效能優化歷程

### 初版：9.5 秒

初版用逐 4-byte Read 載入 vectors.bin（17.5M 次 `f.Read(buf)`），加上 27MB 的 index.json（含所有 chunk text）一次 JSON 解析。

### 優化版：0.34 秒（28x）

三項改動：

| 改動             | 從               | 到                             | 效果               |
| ---------------- | ---------------- | ------------------------------ | ------------------ |
| vectors.bin 讀法 | 逐 4-byte Read   | `os.ReadFile` + `unsafe.Slice` | I/O call 17.5M → 1 |
| metadata 格式    | 含 text（27 MB） | 不含 text（7.3 MB）            | JSON parse 快 4x   |
| text 載入        | 全量             | top-K lazy load（只讀 5 筆）   | 省 19 MB 讀取      |

瓶頸分析：0.34 秒裡、embedding API call（Ollama）約 77ms、file I/O + JSON parse 約 200ms、cosine 計算約 50ms。cosine 計算只佔 15%。

## 通用可複製流程（抽掉 Go/blog）

本案例的 Go 實作細節（`unsafe.Slice`、`os.ReadFile`）是語言特定的、但背後的流程步驟跨語言通用：

1. **Walk corpus**：遞迴掃描目標目錄的所有文件（markdown / code / 任意文字）
2. **Chunk**：段落感知分割、soft token cap、保留語意邊界（原理見 [4.1 Chunking](/llm/04-applications/rag-principles/)）
3. **Embed**：對每個 chunk 呼叫 embedding API（本地 Ollama 或 cloud API），得到固定維度向量
4. **Store**：向量 + metadata + text 分離存檔（binary vectors / compact JSON / lazy-load text）
5. **Search**：embed query → brute-force cosine → top-K → lazy load text for display

Python 實作同流程只是把第 4 步的 binary 檔換成 pickle / FAISS index / SQLite DB、第 5 步的 cosine 換成 numpy / FAISS / sqlite-vec query。Node.js / Rust 同理。

關鍵優化原則也跨語言：「分離向量與文字、query 時只載入向量、top-K 才載入文字」讓 I/O 量從 ~98MB 降到 ~78MB、JSON parse 從 27MB 降到 7MB。這個原則用什麼語言實作都有效。

## 四方案同 corpus Benchmark

用同一個 corpus（24,216 chunks、768 維、nomic-embed-text）比較四種 storage 方案。Benchmark 腳本在 `scripts/blogsearch-bench/bench.py`。

### 前置依賴

Benchmark 腳本讀 Go 工具產生的 index（`.blogsearch/` 下的 `vectors.bin` + `meta.json`）。完整指令鏈：

```bash
cd scripts/blogsearch && go build -o ../../bin/blogsearch .   # build Go 工具
ollama serve &                                                  # 啟動 Ollama
ollama pull nomic-embed-text                                    # pull embedding model
./bin/blogsearch ingest -content content -out .blogsearch       # 建 index（~4 分鐘）
uv run --with sqlite-vec --with faiss-cpu --with numpy \
  scripts/blogsearch-bench/bench.py --index .blogsearch         # 跑 benchmark
```

若無 Go 環境，可用自己的 Python embedding 腳本產生相同格式的 `vectors.bin`（little-endian float32、n × dim 連續排列）+ `meta.json`（`{"dim": 768, "count": n, "metas": [...]}`），benchmark 腳本只讀這兩個檔案、不依賴 Go binary 本身。Corpus 格式無硬性要求，任何目錄下的 `.md` 檔案都可索引。

### 方法論

- **Embedding**：四方案共用同一組 embedding（從 Go index 載入），排除 embedding model 差異
- **Query**：同一句 query（"RAG storage 選型"），跑 5 次取 median
- **Ingest 時間**：只計 storage 操作（不含 embedding），Go 方案含 embedding 不可分離故標 —
- **環境**：macOS Apple Silicon、Python 3.12、Go 1.25

### 結果

| 方案              | Ingest（純 storage） | Query（median） | Index 大小 |
| ----------------- | -------------------- | --------------- | ---------- |
| Go + flat file    | —                    | 151ms           | 97.4 MB    |
| Python sqlite-vec | 2.9s                 | 19ms            | 75.3 MB    |
| Python FAISS flat | 40ms                 | 1.8ms           | in-memory  |
| Python FAISS HNSW | 23.3s                | 0.5ms           | in-memory  |

### 三個關鍵發現

**延遲瓶頸在 I/O 和實作、不在演算法**。Go flat file 的 151ms 裡、cosine 計算約 50ms、file I/O 約 100ms。FAISS flat 用 numpy BLAS 做同樣的 brute-force cosine、純計算 1.8ms — 計算層差約 28 倍（Go pure loop vs BLAS 向量化指令），加上 I/O 後端到端差 84 倍。

**HNSW 的 query 加速在此規模 ROI 低**。FAISS HNSW query 0.5ms vs flat 1.8ms、每次省 1.3ms。但 HNSW build 要 23.3s。每天查 100 次、要 179 天才回本 build 成本（23.3s ÷ 0.13s/天）。4.22 的判讀結論（「此規模 brute-force 夠用」）被數據驗證。

**sqlite-vec 的 19ms 是「DB overhead 換功能」**。比 FAISS flat 慢 10 倍、但多了 SQL metadata filter、transaction 保護、disk persistence。對「需要 filter 但不想維運 server」的場景有意義。

### 讀數據的注意事項

- Go 151ms 含 file I/O（每次 query 重載 78MB）；如果做 daemon mode（常駐、載入一次），query 會降到 ~50ms（純 cosine + overhead）
- FAISS 數字是 in-memory baseline（index 已載入），不含 index 檔案的載入時間
- sqlite-vec 數字含 disk I/O（每次 query 從 SQLite 讀取），是 persistent storage 的真實代價
- 四方案都不含 Ollama embedding call 時間（~77ms），實際端到端延遲要加上

## 二次選型評估：同結論、理由鏈翻轉

Benchmark 數據出來後，80 倍效能差距讓原始選型（Go + flat file）受到質疑：「是否該換 Python + FAISS 或 sqlite-vec？」重新用 WRAP 框架評估，結論相同（維持 Go），但理由鏈完全不同。

### 第一次選型的理由（事前）

「Go 工具鏈統一（mdtools 是 Go）+ 單 binary 分發（clone 後 `go build` 即可）。」

### 實測推翻的前提

| 原始假設             | 實測                                                                                                                                               |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Corpus ~1,500 chunks | 24,216 chunks（16 倍）                                                                                                                             |
| Brute-force < 10ms   | Go 151ms（I/O 瓶頸、不是計算）                                                                                                                     |
| 語言效能差異不大     | Go pure cosine vs numpy BLAS 差 80 倍                                                                                                              |
| 「工具鏈統一」很重要 | mdtools（pre-commit、延遲敏感）跟 blogsearch（手動 CLI、每天幾次）使用模式不同，強制統一語言是用「同一棟建築」邏輯要求「不同用途房間用同一種建材」 |

第一次的理由鏈幾乎全數被推翻。如果只看理由，應該換方案。

### 第二次選型的理由（事後）

重新評估時加入三個第一次沒有的變數：

**端到端延遲 vs in-memory benchmark**。84 倍是端到端的數字（Go 151ms 含 I/O vs FAISS 1.8ms in-memory）。但 FAISS 從 disk 載入 index 也要 ~100-200ms，端到端差距縮小到 2 倍。sqlite-vec 是唯一不需要全量載入的方案（disk-based HNSW、端到端 19ms），差距從「84 倍」變成「8 倍」。

**使用頻率決定 ROI**。CLI 工具、每天 ~10 次手動 query。每次省 130ms（151 vs 19），一天省 1.3 秒。重寫投入 2-3 小時，回本時間 ≈ 19 年。注意這個計算對頻率極敏感：每天 100 次（如被整合進 MCP server 當 agent 工具）回本縮短到 1.9 年、每天 1000 次則 69 天。上方 HNSW ROI 也用每天 100 次計算 — 兩處頻率假設不同是因為比較對象不同（HNSW build 成本 vs 語言重寫成本），但讀者套到自己場景時應先確定自己的查詢頻率。

**Ingest 瓶頸在 Ollama API、跟語言無關**。~4 分鐘的 ingest 裡、embedding API call 佔 95% 以上。換 Python 不會改善 ingest 速度。

### 維持的理由是「痛點不存在」

維持 Go 的理由是**改善的絕對收益太小、投入回不了本** — 151ms 對 CLI 使用模式不構成痛點，與「Go 好」或「工具鏈統一」無關。

### 這個翻轉的教學意義

正確的結論配錯誤的理由是脆弱的。第一次 WRAP 的結論（選 Go）在當時是對的，但理由鏈（工具鏈統一、< 10ms）被實測推翻後，如果不重新建立正確的理由鏈，下次環境變動（比如 blogsearch 從 CLI 變成 API server）就會用已失效的理由做出錯誤判斷。

判讀工具選型時，要區分三層：

1. **結論**：選什麼方案
2. **理由**：為什麼選（可能被推翻）
3. **前提**：理由依賴的假設（規模、使用模式、效能數字）

前提變了、理由就要重建，即使結論沒變。寫進決策紀錄時，三層都要記 — 只記結論的話，下次重新評估時沒有判讀基礎。

區分「正當理由重建」跟「動機性推理」（先有結論再找理由）的判準：新理由是否在看到數據之前也能成立？本例的「130ms 對 CLI 不痛」在實測前也成立（CLI 使用模式本來就低頻），所以是正當重建。如果新理由只能在看到特定數字之後才講得通（如「151ms 剛好在 200ms 閾值內」——但閾值是事後設的），就是 post-hoc rationalization。

### 觸發換方案的訊號

| 訊號                     | 門檻                             | 動作                             |
| ------------------------ | -------------------------------- | -------------------------------- |
| Query 延遲不可接受       | > 500ms                          | 先加 mmap（最小改動）            |
| 使用模式改變             | 從 CLI 變 API server             | 換 Python sqlite-vec             |
| 查詢頻率跳增             | 被整合進 MCP server / agent 工具 | 評估 daemon mode 或換 sqlite-vec |
| Corpus 規模跳增          | > 50K chunks                     | 重跑 benchmark                   |
| 需要原生 metadata filter | code filter 維護成本過高         | 換 Python sqlite-vec             |

## Embedding model 選型（對應 4.12 constraint 優先序）

選 `nomic-embed-text` 的理由鏈：

1. **Ollama 原生支援**：`ollama pull` 一行、不需要額外 Python library 或 API key
2. **體積小**：274 MB、跟 chat model 共用記憶體不打架
3. **已有驗證基線**：rag-demo 用同一個模型跑過 463 chunks、retrieval 命中率確認可用
4. **768 維 sweet spot**：24K chunks × 768 dim × 4 bytes = 70.9 MB，brute-force 可行

未來如果 CJK retrieval 品質不夠（目前可用但未做系統性評估），`multilingual-e5-large` 或 `bge-m3` 是備選。換模型只需改 `embed.go` 的 Model 變數 + 重新 `blogsearch ingest`（4.22 的「四層可替換」設計）。

## CJK 混合 Chunking 觀察

Blog 內容是繁體中文 + 英文術語混合。Chunking 策略沿用 rag-demo 的 paragraph-aware split（空白行切段、soft token cap 400）。

Token 估算用 `len(s) / 2` 的 heuristic（CJK 字元多算一次）。不精確但 chunking 只需要粗略估算。跟 tokenizer 精確計算的差異在 ±20%、對 chunking 品質影響小於 chunk 邊界選擇的影響。

實際觀察：24,216 chunks 的 retrieval 品質在語意搜尋場景（「哪些文章跟 retry 有關」「RAG storage 選型」）表現良好。keyword 精確搜尋場景（「找 RFC 7807」）表現較弱 — 這是 embedding-only retrieval 的已知限制（見 4.1 的語意 vs 字面相似度對比），未來可加 BM25 做 hybrid search。

## 跟其他章節的對應

| 本案例的段落     | 對應原理章節                                                                       |
| ---------------- | ---------------------------------------------------------------------------------- |
| 選型過程         | [4.22 演化階梯 + 工程約束](/llm/04-applications/vector-storage-engineering/)       |
| 二次選型評估     | [4.22 同 corpus 實測比較](/llm/04-applications/vector-storage-engineering/)        |
| Embedding 選型   | [4.12 實務選型 constraint 優先序](/llm/04-applications/embedding-model-internals/) |
| Chunking         | [4.1 Chunking 策略對比](/llm/04-applications/rag-principles/)                      |
| Benchmark 方法論 | [4.14 Benchmarking 方法論](/llm/04-applications/benchmarking-and-evaluation/)      |
| Storage 格式設計 | [4.10 衍生產物管理](/llm/04-applications/artifact-management/)                     |
| Retrieval 品質   | [4.1 Retrieval 失敗根因](/llm/04-applications/rag-principles/)                     |
