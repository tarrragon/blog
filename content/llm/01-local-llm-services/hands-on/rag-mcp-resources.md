---
title: "Hands-on：RAG / MCP 的資源 footprint"
date: 2026-05-12
description: "RAG ingest / query / MCP server 三階段的 RAM / 磁碟 / process 實測、多模型並存的 RAM 衝突、本地 LLM 跑 RAG 跟單純 chat 的差異"
tags: ["llm", "hands-on", "rag", "mcp", "resource"]
weight: 9
---

[Resource management 章](/llm/01-local-llm-services/hands-on/resource-management/) 講的是 Ollama / ComfyUI 等[推論伺服器](/llm/knowledge-cards/inference-server/)的 lifecycle。但**跑 [RAG](/llm/knowledge-cards/rag/) / [MCP](/llm/knowledge-cards/mcp/) 應用**比單純 chat 多吃幾倍資源——[embedding model](/llm/knowledge-cards/embedding-model/)、chat model、index 檔、subprocess、tool 邏輯——而且不同階段（ingest vs query）的瓶頸不一樣。

本篇紀錄 [RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/) 跟 [MCP demo](/llm/01-local-llm-services/hands-on/mcp-demo/) 跑起來的實測資源 footprint、提供本地多模型並存的 baseline、給寫 production 應用前的 sanity check。

> **驗證日期**：2026-05-12
> **環境**：M4 Pro 32 GB、Ollama 0.23.2、Python 3.14
> **Corpus**：本 blog 的 `content/llm/`、71 個 markdown 檔、463 chunks

## 三階段資源 footprint

RAG / MCP 工作流通常分三階段、各自吃不同資源：

| 階段           | 主要資源消耗                             | 持續時間                    | 是否常駐             |
| -------------- | ---------------------------------------- | --------------------------- | -------------------- |
| **RAG ingest** | embedding model RAM + CPU + 磁碟寫       | one-shot（corpus 更動時跑） | 否                   |
| **RAG query**  | index 載入 RAM + chat model RAM + GPU    | per-request                 | retrieval index 常駐 |
| **MCP server** | subprocess 永久跑、tool 呼叫時動態載資源 | session 內常駐              | 是                   |

不同階段的瓶頸不一樣、優化目標也不同。

## RAG Ingest 階段：one-shot 但批次密集

跑 `python3 scripts/rag-demo/ingest.py` 時：

```text
Found 71 markdown files under content/llm
  [10/71] 86 chunks in 4.5s
  [20/71] 181 chunks in 8.6s
  ...
  [70/71] 461 chunks in 22.2s
Wrote 463 records to scripts/rag-demo/index.pkl (22.3s)
```

實測資源消耗：

| 資源        | 數字                                             | 為什麼                                                                   |
| ----------- | ------------------------------------------------ | ------------------------------------------------------------------------ |
| RAM（峰值） | ~600 MB                                          | nomic-embed-text 模型 (274 MB) + Python runtime + 累積 records (~200 MB) |
| 磁碟寫      | `index.pkl` ~3.7 MB                              | 463 records、每筆含 chunk text + 768-dim float embedding                 |
| CPU + GPU   | Ollama 推 embedding、Apple Silicon Metal backend | 22 秒處理 463 個 chunk、平均 ~21 chunk/sec                               |
| 網路        | 0                                                | 完全本地推論                                                             |

**Ingest 階段的特性**：

- **One-shot**：corpus 不變不用重跑、index 寫一次永久用。
- **吃 CPU 多於 RAM**：產生 embedding 是 forward pass、瓶頸在 GPU 算力、RAM 沒太大壓力。
- **磁碟寫小**：每 chunk 約 8 KB（text 部分 ~5 KB + embedding 768 floats × 4 bytes = ~3 KB）、463 chunks 總共 ~3.7 MB。
- **可平行**：sequential `embed(chunk)` 是最慢實作、用 batching API（如果 Ollama 支援）或多 worker、能快 5-10x。

**規模 extrapolation**：

| Corpus 大小                                 | 預估 ingest 時間 | index.pkl 大小 |
| ------------------------------------------- | ---------------- | -------------- |
| 71 docs / 463 chunks（本 blog）             | 22 秒            | 3.7 MB         |
| 1000 docs / ~7000 chunks（中型 codebase）   | ~5 分鐘          | ~55 MB         |
| 10000 docs / ~70000 chunks（大型 codebase） | ~50 分鐘         | ~550 MB        |
| 100K docs / ~700K chunks（公司 wiki）       | ~8 小時          | ~5.5 GB        |

10K docs 以上就應該考慮：

- [Batching](/llm/knowledge-cards/batching/) embedding（單次 request 送 50 個 chunks）
- 並行 worker（Python multiprocessing、4-8 worker）
- 換 [vector database](/llm/knowledge-cards/vector-database/)（避免把全部資料用 pickle 塞 RAM）

## RAG Query 階段：retrieval 加 generation

跑 `python3 scripts/rag-demo/query.py --show-retrieved "問題"` 時：

```text
Loaded 463 chunks from scripts/rag-demo/index.pkl
=== Retrieved chunks ===
  0.870  llm/knowledge-cards/transformer.md#chunk2
  ...
（LLM 生成 response）
```

實測資源消耗（單次 query）：

| 階段                       | RAM 增量                                | 時間                              |
| -------------------------- | --------------------------------------- | --------------------------------- |
| 載 index.pkl 到 RAM        | 3.7 MB（小 corpus）/ MB 級（大 corpus） | < 1 秒                            |
| embed query                | 0（已載入的 nomic-embed-text）          | 200 ms                            |
| cosine over 463 chunks     | 純 Python 計算、暫時用 ~10 MB           | 50 ms                             |
| 載 chat model（gemma3:1b） | ~1 GB（首次）/ 0（已 cached）           | 5-10 秒（首次）/ 0（cached）      |
| 生成 response              | 0 額外                                  | 5-30 秒（看 model + prompt 長度） |

**Query 階段的特性**：

- **第一次 cold start**：要載 chat model 進 RAM、5-10 秒首字延遲。
- **後續 query 都快**：embedding model + chat model 都在 RAM、retrieval 毫秒級、只剩 generation 時間。
- **RAM 占用 = embedding model + chat model + index**：
    - 463 chunks: 274 MB + chat model + 3.7 MB ≈ chat model + 280 MB
    - 100K chunks: 274 MB + chat model + ~800 MB 進 RAM、加上 mmap pickle 額外開銷
- **瓶頸是 chat model**：retrieval 部分快、瓶頸完全在 generation。

**多模型並存**（embedding + chat）：

```bash
# 看當前 RAM 占用
ollama ps
# NAME                       SIZE      UNTIL
# nomic-embed-text:latest    274 MB    4 minutes from now
# gemma3:4b                  5.5 GB    4 minutes from now
```

兩個 model 都載入時、Ollama RAM 占用約 6 GB。Ollama 的 `OLLAMA_KEEP_ALIVE`（預設 5 分鐘）會 idle 後分別 unload 兩個 model。

**規模 sanity check**：

| 場景                                               | RAM 需求 |
| -------------------------------------------------- | -------- |
| 純 chat（gemma3:1b）                               | ~1 GB    |
| RAG with gemma3:1b + nomic-embed-text + 小 index   | ~1.5 GB  |
| RAG with gemma3:4b + nomic-embed-text + 中型 index | ~6 GB    |
| RAG with gemma4:31b + nomic-embed-text + 大 index  | ~20 GB   |

跑 RAG 比 chat 額外要 ~300-1000 MB（embedding model + index）、不會太重。

## MCP Server 階段：subprocess 常駐

跑 `python3 scripts/mcp-demo/test_client.py` 時、client 會 spawn `blog_mcp_server.py` 當 child process。

實測：

| 資源            | 數字                       | 備註                                  |
| --------------- | -------------------------- | ------------------------------------- |
| Subprocess RAM  | ~50 MB                     | Python runtime + index.pkl mmap       |
| stdio pipe 數量 | 3（stdin、stdout、stderr） | 每 spawn 一個 server 都要 3 FD        |
| 持續時間        | client 在跑就在跑          | client 結束時 SIGPIPE 自動結束 server |

**MCP server 的特性**：

- **每個 client spawn 一個 server**：Claude Desktop 開 5 個 MCP server、就有 5 個 Python subprocess。
- **Index lazy load**：本 demo `load_index()` 第一次 call 才 read pickle、之後 cached。Cold start 第一次 tool call 稍慢。
- **Process lifecycle 在 client 端**：client 死了、stdin EOF、server 自然結束。Client 沒清乾淨 spawn 多次就 leak process。

```bash
# 看當前所有 MCP server
ps aux | grep blog_mcp_server | grep -v grep

# 如果 client crash 留下 zombie：
pkill -f "blog_mcp_server.py"
```

**多 MCP server 並存**（如 Claude Desktop 接 git server + filesystem server + custom server）：

| Server                     | RAM                | 主要負載              |
| -------------------------- | ------------------ | --------------------- |
| git MCP server             | ~30 MB             | shell 呼叫            |
| filesystem MCP server      | ~30 MB             | fs 操作               |
| blog_mcp_server（本 demo） | ~50 MB（含 index） | embedding + retrieval |
| 5 個 server 同時           | ~200 MB            | 累積                  |

200 MB 在 32 GB Mac 上不顯眼、但 16 GB Mac + 多 MCP server + 大 chat model 就可能擠到。

## RAG + MCP 整合：完整應用 stack

實際應用會疊起來：

```text
User 在 Claude Desktop 打字
  ↓
Claude Desktop (~200 MB)
  ↓ MCP stdio
blog_mcp_server.py (~50 MB)
  ↓ HTTP /api/embeddings + /v1/chat/completions
Ollama daemon (~200 MB)
  ↓ load
nomic-embed-text 模型 (~274 MB) + 主 chat model (~6 GB)
```

整體 RAM 占用範圍：

| 配置                                           | 估算    |
| ---------------------------------------------- | ------- |
| Minimal（gemma3:1b + 小 index）                | ~1.7 GB |
| Standard（gemma3:4b + 中 index）               | ~6.5 GB |
| Heavy（gemma4:31b + 大 index + 多 MCP server） | ~22 GB  |

跟 [resource-management 章](/llm/01-local-llm-services/hands-on/resource-management/) 比、RAG / MCP 加 ~500 MB-1 GB overhead 在 chat 之上、是合理的 tradeoff（換來 retrieval + tool use 能力）。

## 各資源類型的關鍵指標

整理三 dimension 的關鍵指標跟監控方式：

### RAM

```bash
# 看 Ollama 載了哪些 model
ollama ps

# 看所有 LLM-related process
ps aux | grep -E "ollama|comfyui|mcp" | grep -v grep | awk '{print $4, $11, $12, $13}' | sort -rn

# 系統整體
vm_stat | head -3
```

**告警閾值**：

- RAM 占用 > 80% 系統總量：開始考慮 unload model 或關掉 ComfyUI
- 看到 swap 增加（`vm_stat | grep "Swapouts"`）：已經 swap、要立刻減少 model

### 磁碟

```bash
# Ollama models 累積
du -sh ~/.ollama/models

# RAG index 累積（多個 corpus）
du -sh scripts/rag-demo/index*.pkl 2>/dev/null

# ComfyUI checkpoints / VAE / LoRA / etc
du -sh ~/Projects/ComfyUI/models/*
```

**累積評估**：

- Ollama: 每 model 1-20 GB、半年累積容易破 50 GB
- RAG index: 每 100K chunks ~800 MB、多 corpus 累積要管
- ComfyUI: 每 checkpoint 4-7 GB、加 LoRA / VAE / ControlNet 等可達 50+ GB

### Process / Port

```bash
# 一鍵 audit 所有 LLM service
for p in 11434 1234 8080 8188 8000; do
  echo "=== port $p ==="
  lsof -i :$p 2>/dev/null | head -2
done

# 找 zombie subprocess（沒 parent 的 mcp server）
ps aux | grep "mcp_server" | grep -v grep
```

**告警訊號**：

- 同 port 兩個 process listen：明顯有 zombie、要 kill
- 多個 mcp_server PPID = 1（被 reparent 到 init）：原 client 死了沒清乾淨

## RAG 應用的長期累積管理

跑超過幾週、會累積：

| 累積物               | 為什麼累積                         | 怎麼清                                                               |
| -------------------- | ---------------------------------- | -------------------------------------------------------------------- |
| Multiple `index.pkl` | 跑不同 corpus 各建 index、舊的沒刪 | `find scripts -name 'index*.pkl' -mtime +30 -delete`                 |
| Ollama models        | 試了不同 model 沒清                | 看 `ollama list` modified 欄、`ollama rm` 不用的                     |
| Python `__pycache__` | 每次跑 script 累積                 | `.gitignore` 已包、本地 `find . -name __pycache__ -exec rm -rf {} +` |
| Embedding cache      | 如果你寫了 embedding cache 機制    | 各自清理策略                                                         |

清理 idiom：

```bash
# 每月跑一次的 cleanup
llm-rag-cleanup() {
  echo "[*] Old indexes (>30 days):"
  find scripts -name 'index*.pkl' -mtime +30 -ls
  echo "[*] Ollama models (review):"
  ollama list
  echo "[*] Python caches:"
  find ~/Projects -name __pycache__ -type d | head -10
}
```

## 跟 production 的差距預告

本篇紀錄的數字、是「single-user、single-machine、no concurrency」的 baseline。Production 場景多了幾個維度：

| 維度           | 本地             | Production                     |
| -------------- | ---------------- | ------------------------------ |
| 並發 user      | 1                | 10-10000                       |
| Index 大小     | < 100 MB         | TB 級                          |
| Model serving  | Ollama 1 process | vLLM / TGI / Triton 多 worker  |
| Vector storage | pickle           | Pinecone / Weaviate / pgvector |
| Latency 要求   | 秒級 OK          | p50 < 500ms、p99 < 2s          |
| Cost model     | 一次性硬體       | $/request、$/token             |
| Observability  | tail log         | metrics / traces / dashboards  |
| 失敗模式       | crash → 自己重啟 | 99.9% uptime SLA               |

Production 視角詳細展開見 [4.5 Production 部署的資源評估原理](/llm/04-applications/production-resource-planning/)。

## 何時這篇會過時

**不會過時的部分**：

- 三階段 footprint 分類（ingest / query / server）
- RAM / 磁碟 / process 三 dimension 的監控指令
- 多模型並存的 RAM 預估方法
- 長期累積管理 idiom

**會變的部分**：

- 具體 RAM / 磁碟數字（隨模型架構、量化方法演化）
- `OLLAMA_KEEP_ALIVE` 等具體環境變數名
- 哪些 vector DB 主流（會持續演化）

讀的時候若 RAM 占用跟本篇對不上、可能是新 model 架構效率改變、用同樣方法量自己環境的 baseline 即可。

跟其他 hands-on 章節的關係：完整 hands-on 系列見 [Hands-on 章節索引](/llm/01-local-llm-services/hands-on/)、實作配對見 [RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/) 跟 [MCP demo](/llm/01-local-llm-services/hands-on/mcp-demo/)、Ollama / ComfyUI 共用的 lifecycle 管理見 [Resource management](/llm/01-local-llm-services/hands-on/resource-management/)、Apple Silicon 統一記憶體預算原理見 [0.5 記憶體預算](/llm/00-foundations/hardware-memory-budget/)。

## 跑這篇實測的指令總結

```bash
# 1. RAG ingest 階段 RAM 量
ollama ps  # 先看 baseline
python3 scripts/rag-demo/ingest.py &
INGEST_PID=$!
ollama ps  # 看 embedding model 載入後
vm_stat | head -3
wait $INGEST_PID

# 2. RAG query 階段 RAM 量
ollama ps  # 看 idle 後 unload
python3 scripts/rag-demo/query.py --show-retrieved "test query"
ollama ps  # 看 chat model 載入

# 3. MCP server 階段 process / RAM
python3 scripts/mcp-demo/test_client.py &
CLIENT_PID=$!
sleep 2
ps aux | grep blog_mcp_server | grep -v grep
wait $CLIENT_PID

# 4. 完成釋放
ollama list | tail -n +2 | awk '{print $1}' | xargs -I {} \
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"{}\",\"keep_alive\":0}"
```
