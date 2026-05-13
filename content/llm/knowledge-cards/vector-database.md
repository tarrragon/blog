---
title: "Vector Database"
date: 2026-05-12
description: "為高維向量 (embedding) 設計的儲存 + 近似最近鄰 (ANN) 檢索系統：RAG 從 prototype 跨到 production 的關鍵元件"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Vector Database 的核心概念是「**為高維向量設計的儲存系統 + 近似最近鄰 (Approximate Nearest Neighbor, ANN) 檢索引擎**」。是 [RAG](/llm/knowledge-cards/rag/) 系統從 prototype 跨到 production 的關鍵元件——當 [embedding](/llm/knowledge-cards/embedding-model/) index 大到記憶體裝不下、或並發 query 量超過單機處理能力、就要從 pickle / in-memory 升級到 vector DB。

## 概念位置

Vector DB 跟傳統 SQL / NoSQL database 並列、但專精「向量相似度搜尋」這個操作。它不取代傳統 DB——通常 LLM 應用是兩者並用：傳統 DB 存結構化資料（user / metadata）、vector DB 存 embedding + chunk text。實作上、近期主流是「向量加進去現有 DB」（如 Postgres 的 pgvector extension）或「專用服務」（如 Pinecone、Weaviate、Qdrant）。

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

## 設計責任

選 vector DB 之前回答四個問題：

1. **Corpus 規模**：決定 hosted vs self-host 取捨。
2. **Update 頻率**：每天一次（適合 batch rebuild）vs 即時（要 incremental update 支援）。
3. **Latency 目標**：< 50ms 要 in-memory HNSW、可接受 200ms 用 disk-based。
4. **Hybrid search 需求**：純向量 vs 向量 + filter（如「embedding 相似 + tag = code」），影響 schema 設計。

衍生產物管理上、vector DB 屬於 [external 類別](/llm/04-applications/artifact-management/)——index content 不進 git、用 manifest（如 schema definition + ingest script + version tag）描述。Build pipeline 從 source corpus 自動 rebuild。

不適合 vector DB 的情境：knowledge 高度結構化（直接 SQL）、corpus 小（pickle 就好）、單次 retrieval（off-line 跑、不開 server）。
