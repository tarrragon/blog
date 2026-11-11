---
title: "Vector Database"
date: 2026-05-12
description: "為高維向量 (embedding) 設計的儲存 + 近似最近鄰 (ANN) 檢索系統：RAG 從 prototype 跨到 production 的關鍵元件"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Vector Database 的核心概念是「**為高維向量設計的儲存系統 + 近似最近鄰 (Approximate Nearest Neighbor, ANN) 檢索引擎**」。是 [RAG](/llm/knowledge-cards/rag/) 系統從 prototype 跨到 production 的關鍵元件——當 [embedding](/llm/knowledge-cards/embedding-model/) index 大到記憶體裝不下、或並發 query 量超過單機處理能力、就要從 pickle / in-memory 升級到 vector DB。

## 跟其他概念的關係

Vector DB 跟傳統 SQL / NoSQL database 並列、但專精「向量相似度搜尋」這個操作。它不取代傳統 DB——通常 LLM 應用是兩者並用：傳統 DB 存結構化資料（user / metadata）、vector DB 存 embedding + [chunk](/llm/knowledge-cards/chunking/) text。實作上、近期主流是「向量加進去現有 DB」（如 Postgres 的 pgvector extension）或「專用服務」（如 Pinecone、Weaviate、Qdrant）。

## 可觀察訊號與例子

主流選擇分類：

| 類別              | 例子                                   | 適合                        |
| ----------------- | -------------------------------------- | --------------------------- |
| Hosted SaaS       | Pinecone、Weaviate Cloud、Qdrant Cloud | 不想 maintain、流量大       |
| Self-host service | Weaviate、Qdrant、Milvus               | 內部部署、控制 cost         |
| Embedded library  | FAISS、HNSWLib、Annoy                  | 嵌進應用、單機規模          |
| DB extension      | pgvector、SQLite + vec                 | 已有 SQL DB、加 vector 能力 |

關鍵 ANN 演算法：

- **HNSW**（Hierarchical Navigable Small World）：主流、sublinear 查詢、犧牲少許精度
- **IVF**（Inverted File Index）：分組索引、適合超大規模
- **Flat**（exhaustive search）：精確但 O(n)、小資料集 OK

scale 對照（基於 [4.9 production](/llm/04-applications/production-resource-planning/) 跟 [RAG/MCP resources](/llm/01-local-llm-services/hands-on/rag-mcp-resources/) 章節）：

| Corpus 規模  | 適合                                                                                            |
| ------------ | ----------------------------------------------------------------------------------------------- |
| < 10K chunks | Python pickle / in-memory list（[本 blog demo](/llm/01-local-llm-services/hands-on/rag-demo/)） |
| 10K-100K     | FAISS / embedded library                                                                        |
| 100K-10M     | Self-host vector DB                                                                             |
| > 10M        | Hosted SaaS 或分散式 cluster                                                                    |

## 判斷條件與後果

選 vector DB 時，corpus 規模、update 頻率、latency 目標與 hybrid search 需求各自排除不合用的部署方式或 index：

1. **Corpus 規模**：規模決定 hosted 與 self-host 的取捨。規模越大，self-host 要自己維運的 index 與機器越多；hosted 服務把這份維運換成費用。
2. **Update 頻率**：每天更新一次時，batch rebuild 整份 index 就夠；新資料要即時查得到時，DB 必須支援 incremental update，否則新文件要等下一次 rebuild 才進得了 index。
3. **Latency 目標**：要 50ms 以下時，HNSW index 必須放在記憶體裡；能接受 200ms 時，disk-based 的 index 可用，記憶體需求較低。
4. **Hybrid search 需求**：查詢除了 embedding 相似，還要加 filter（如 tag = code）時，filter 用的欄位必須在 schema 裡，DB 也要支援向量與 filter 一起查；純向量查詢沒有這兩項限制。

Vector DB 的 index 是從 source corpus 生成的衍生產物，屬於 [external 類別](/llm/04-applications/artifact-management/)：index content 隨時可以由 ingest script 從 corpus 重建，所以 git 裡放的是描述它的 manifest（schema definition、ingest script、version tag），build pipeline 從 source corpus 自動 rebuild index。

Knowledge 高度結構化、corpus 很小，或只做一次離線 retrieval 時，vector DB 的 server 與 index 維運換不到好處：結構化資料用 SQL 查得到精確結果，小 corpus 放在 pickle 就夠，離線跑一次的 retrieval 不需要常駐的 server。

Storage 升級判讀（什麼規模該從 in-memory 升級到 vector DB）、index 生命週期、dependency 約束的工程分析見 [4.22 RAG storage 工程](/llm/04-applications/vector-storage-engineering/)。
