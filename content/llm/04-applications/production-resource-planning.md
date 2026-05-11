---
title: "4.5 Production 部署的資源評估原理"
date: 2026-05-12
description: "從本地單 user 到 production multi-tenant：concurrent users、cost model、observability、SLA、capacity planning 的設計取捨"
tags: ["llm", "applications", "production", "deployment", "resource-planning"]
weight: 5
---

LLM 應用從本地實驗跨到 production 是個 phase transition、不是線性放大。本地 single-user 場景的「跑得起來」變 production 場景就要回答全新一組問題：100 個 user 同時打進來怎麼辦、每個 [token](/llm/knowledge-cards/token/) 要多少錢、p99 latency 怎麼控、model service down 了怎麼處理。

本章寫的是「**從本地實驗 → production 該想清楚的維度**」、focus 在跨工具世代不變的原理。具體 framework（vLLM、TGI、Triton、SGLang）跟雲端服務（OpenAI / Anthropic / Bedrock）的選型不展開——這些半年一個世代、寫了會過時。本章建立的是「無論用哪套工具、都該回答」的設計取捨清單。

跟 [4.0 RAG](/llm/04-applications/rag-principles/) / [4.1 Tool use](/llm/04-applications/tool-use-principles/) / [4.2 Agent](/llm/04-applications/agent-architecture/) 對應「應用怎麼設計」、本章對應「應用怎麼跑」。

## 本章目標

讀完本章後、你應該能：

1. 列出 production LLM 部署該評估的 6 個 dimension。
2. 解釋 single-user benchmark 為什麼不能直接 extrapolate 到 multi-user 場景。
3. 區分 latency-sensitive 跟 throughput-sensitive 應用的設計差別。
4. 對成本模型（$/request、$/token、$/month）做合理估算。

## 從本地到 production 的 phase transition

本地 LLM 跑 [RAG](/llm/knowledge-cards/rag/) / [MCP](/llm/knowledge-cards/mcp/) 的 baseline（[hands-on 章節](/llm/01-local-llm-services/hands-on/rag-mcp-resources/)）：

| 維度         | 本地（single-user） |
| ------------ | ------------------- |
| 並發 user    | 1                   |
| Latency 要求 | 秒級 OK             |
| Index 大小   | < 100 MB            |
| Cost         | 一次性硬體          |
| Uptime       | 自己重啟            |
| 觀測         | `tail log`          |

Production 場景每個維度都跳一個量級：

| 維度         | Production（multi-tenant）        |
| ------------ | --------------------------------- |
| 並發 user    | 10 - 10000                        |
| Latency 要求 | p50 < 500 ms、p99 < 2 s           |
| Index 大小   | GB - TB                           |
| Cost         | $ / request、$ / token、$ / month |
| Uptime       | 99.9% SLA                         |
| 觀測         | metrics、traces、dashboards       |

每個維度跳一個量級的 implication 不是「資源 × 10」、是「全新的失敗模式 + 新的設計取捨」。

## 維度 1：Concurrent users / Throughput

### 為什麼這個維度最關鍵

本地 single-user 的 baseline 數字（[hands-on](/llm/01-local-llm-services/hands-on/rag-mcp-resources/) 紀錄的 RAM / latency）**幾乎不能 extrapolate** 到 multi-user：

- 100 個 user 同時送 request → 不是「同樣 latency × 100」、是「queueing + memory contention + GPU 排隊」、單個 user 的 latency 可能漲 10×
- 同樣 model 服務 N 個 user → KV cache 占用要乘以 N、單個 GPU 可能裝不下
- Single-user 「200 ms latency」可能 production 變「p99 5 秒」

### Key concept：batching

[Batching](/llm/knowledge-cards/batching/) 跟 [KV cache](/llm/knowledge-cards/kv-cache/) 設計讓 GPU 能多 user 的 request 一次 forward pass、是 production [inference server](/llm/knowledge-cards/inference-server/) 的核心優化。但 batching 也帶取捨：

- **靜態 batching**：等湊滿 N 個 request 才跑、提高 throughput、犧牲首字延遲
- **連續 batching（continuous batching）**：vLLM / TGI 等用、新 request 動態加入正在跑的 batch、平衡 throughput + latency
- **No batching**：每 request 獨立跑、latency 低、GPU 利用率差

選 batching 策略主要取決於 latency 跟 throughput 哪個重要：

| 應用場景                                        | 適合 batching 策略                                                 |
| ----------------------------------------------- | ------------------------------------------------------------------ |
| 互動式對話（IDE plugin、chatbot UI）            | continuous batching、低 latency 優先                               |
| 批次處理（document summarization、code review） | static batching、throughput 優先                                   |
| Embedding 服務                                  | batching 越大越好、embedding 是純 forward pass、batch 16-128 都 OK |

### 評估 concurrent throughput

要做的測試（不在本章 hands-on、是 framework）：

1. **Single-user baseline**：measure single request 在 idle server 上的 latency
2. **N-user load test**：用 [k6](https://k6.io) / [vegeta](https://github.com/tsenart/vegeta) / 自寫 async client 跑 1、10、100 個並發 request
3. **觀察 p50 / p95 / p99 latency 隨並發數變化**：通常 < N=batch_size 時平、超過 batch_size 後 latency 線性漲
4. **GPU memory 飽和點**：tokens-in-flight 超過某個量、新 request 開始排隊

實務評估公式：

```text
Max concurrent users (steady state)
    = (GPU memory available - model weights) / (per-user KV cache size)
```

例：H100 80 GB - 31B model 60 GB = 20 GB 可用 / 每 user 平均 200 MB KV cache = 100 個並發 user。

但這是上限、實際還要考慮 latency target。

## 維度 2：Latency budget

### Latency-sensitive vs throughput-sensitive

兩類應用的設計取捨完全不同：

| 屬性          | Latency-sensitive                   | Throughput-sensitive                |
| ------------- | ----------------------------------- | ----------------------------------- |
| 範例          | IDE 補完、chat UI、search assistant | 批次標籤、文件摘要、離線 RAG ingest |
| 目標 metric   | p99 latency                         | tokens / second / GPU               |
| User 經驗影響 | 直接（卡住）                        | 間接（總時間）                      |
| Batching      | 小 batch / continuous               | 大 batch                            |
| 資源規劃      | 預留 headroom 給 spike              | 跑滿 GPU 利用率                     |

混合應用（如 chat with RAG）有兩段：retrieval（throughput-friendly、可 batch）+ generation（latency-sensitive、要 stream）。兩段獨立優化。

### Latency 預算分配

一個 RAG 應用的 p99 latency 是各段加總：

```text
Total p99 = client → API gateway → retrieval → LLM prefill → LLM decode → response stream
         ≈ 50 ms      20 ms        50 ms        500 ms       1500 ms      100 ms
         ≈ 2.2 seconds
```

如果 p99 budget 是 2 秒、要先確認**最大消耗段是哪個**：

- 通常 LLM generation 是最大、是優化重心
- Retrieval 在大 corpus 場景可能超過 100 ms、要 index 優化（HNSW、近似 nearest neighbor）
- API gateway 通常可忽略、超過 50 ms 就有 SRE 議題

各段監控分開、不要只看 total latency——找不到 root cause。

## 維度 3：Cost model

### 三種計費單位

| 單位          | 怎麼算                     | 適合                                      |
| ------------- | -------------------------- | ----------------------------------------- |
| $/request     | 每 API call 固定價         | 簡單應用、可預測流量                      |
| $/token       | 看 input + output token 數 | OpenAI / Anthropic 主流、混合輸入長度應用 |
| $/server-hour | 自家跑 GPU instance、月租  | 高 throughput、可預測 utilization         |

雲端 API（OpenAI / Anthropic）幾乎都 $/token、給定 model 不同 price tier。自家跑（vLLM on Lambda Labs / RunPod）是 $/server-hour。

### 成本估算 worked example

假設應用：

- 1000 active users / day
- 每 user 平均 10 requests / day
- 每 request 平均 1000 input tokens + 500 output tokens
- 用 Claude Sonnet 4.6（假設 $3 input / $15 output per million tokens）

每日 cost：

```text
total_requests = 1000 × 10 = 10000 / day
input_tokens = 10000 × 1000 = 10M
output_tokens = 10000 × 500 = 5M
daily_cost = 10M × $3/M + 5M × $15/M = $30 + $75 = $105 / day
monthly_cost ≈ $3150
```

跑自家 GPU 比較：

```text
H100 instance: ~$2/hour on Lambda Labs
H100 monthly = $2 × 24 × 30 = $1440
若 utilization > 50%、自架較划算
若 utilization < 30%、API 較划算
```

**Breakeven 點通常在「持續高 utilization」**——尖峰流量短的應用、API 更划算（不用養閒置 capacity）。

### Hidden cost

容易漏算的：

- **Egress bandwidth**：cloud GPU instance 出流量、AWS / GCP 都 $/GB
- **Storage**：vector DB / log retention / metric retention
- **失敗 retry**：5xx error 自動 retry、token 重算
- **Cold start**：scale-to-zero 設定、cold start 浪費 5-30 秒 GPU time / 次

## 維度 4：Storage / Vector DB

本地 [RAG](/llm/knowledge-cards/rag/) demo 用 pickle、production 不行——pickle 不支援並發 read、不支援 update、不支援 partition、必須換 [vector database](/llm/knowledge-cards/vector-database/)。

### Vector DB 的設計取捨

| 維度                        | 取捨                                                         |
| --------------------------- | ------------------------------------------------------------ |
| **Hosted vs self-host**     | Hosted（Pinecone、Weaviate Cloud）省維護、self-host 控制成本 |
| **In-memory vs disk-based** | In-memory 快但記憶體限制、disk-based 大但 latency 高         |
| **HNSW vs flat**            | HNSW 近似但 sublinear、flat 精確但 linear                    |
| **Update strategy**         | Periodic batch index rebuild vs incremental update           |

具體選型半年一變、本章不展開。**設計時要回答的問題**：

1. Corpus 多大？1M 以下 in-memory 就好、1M 以上要 disk-based
2. Update 頻率？每天一次 vs 即時、影響 architecture
3. Latency target？< 50 ms 要 in-memory / HNSW、< 200 ms 用 disk-based
4. 並發 query 量？每秒 100 query 跟每秒 10000 query 設計完全不同

### Index 大小成長

從 hands-on 章節 extrapolate：

| Corpus 規模 | Index 大小（含 chunks + embeddings） |
| ----------- | ------------------------------------ |
| 1K docs     | ~50 MB                               |
| 100K docs   | ~5 GB                                |
| 1M docs     | ~50 GB                               |
| 10M docs    | ~500 GB                              |
| 100M docs   | ~5 TB                                |

10M docs 以上、單機塞不下、要 sharding + 分散式 index。

## 維度 5：Observability

Single-user `tail log` 不夠 production 用。要看的 metric：

### Latency metrics

- **TTFT (Time to First Token)**：user-perceived「響應時間」、streaming 場景關鍵
- **TPS (Tokens per second)**：generation 速度
- **End-to-end latency**：含 retrieval + LLM + post-processing
- **Per-percentile breakdown**：p50 / p90 / p95 / p99——p99 反映最差 user 體驗

### Throughput metrics

- **Requests per second**：API 端 RPS
- **Tokens per second**（aggregate）：GPU 整體 throughput
- **Queue depth**：等待 batch 的 request 數量、暴漲表示 overload

### Cost metrics

- **$ per active user per day**：產品經濟學基本盤
- **Cost per session**：互動式應用單位成本
- **Cache hit rate**：prompt cache / embedding cache 命中率、直接影響 cost

### Quality metrics

- **Refusal rate**：模型 refuse 回應的比例
- **Hallucination rate**：（要 reviewer 標）
- **User feedback score**：thumb up / down

### 工具：metrics / traces / logs 三層

```text
Metrics（Prometheus / Datadog / CloudWatch）
    → time-series、aggregate、適合 alerting
Traces（OpenTelemetry / Datadog APM）
    → per-request、可追蹤跨服務 latency
Logs（structured JSON、推 ELK / Loki）
    → 詳細 context、debug 用
```

三層各司其職、不要 conflate。Metric 看到 p99 漲、用 trace 找哪個 request 哪段慢、用 log 看那 request 的具體 prompt / response。

## 維度 6：Reliability / SLA

### 可預期的失敗模式

| 失敗類型                    | 處理                                         |
| --------------------------- | -------------------------------------------- |
| **Transient GPU OOM**       | retry with smaller batch、circuit breaker    |
| **Inference timeout**       | 切短 max_tokens、拒絕過長 prompt             |
| **Model server crash**      | health check + auto-restart（systemd / k8s） |
| **Vector DB unavailable**   | fallback：跳過 RAG、純 chat 答               |
| **Upstream API rate limit** | exponential backoff + jitter                 |

### Graceful degradation

設計 production LLM 應用、要回答「失敗時降級到什麼」：

| Component down            | Acceptable degradation                             |
| ------------------------- | -------------------------------------------------- |
| Vector DB                 | 用 LLM 內知識回答 + 標明「未查最新文件」           |
| RAG retrieval 但 LLM 仍跑 | 用退役 cache 結果 + retry                          |
| Primary LLM API           | fallback 到 secondary（OpenAI ↔ Anthropic ↔ 本地） |
| 全部 down                 | 顯示維護頁、不要 5xx                               |

每個 fallback 路徑都要先設計、不能等出事再決定。

### Capacity planning

簡單公式：

```text
Required capacity = peak_concurrent_users × per_user_RAM
                  × overhead_factor (1.3-1.5)
                  × redundancy_factor (2x for HA)
```

例：peak 100 並發、每 user ~500 MB KV cache、overhead 1.3、HA 2x → 130 GB GPU memory。一張 H100 不夠、要兩張 A100 80GB 或 H100 + sharding。

## 跟本地 hands-on 的對照

| 維度                | 本地 hands-on 紀錄              | Production 該量什麼            |
| ------------------- | ------------------------------- | ------------------------------ |
| Single-user latency | 30-60s for SDXL、5-20s for chat | p50 / p95 / p99 latency        |
| Index size          | ~3.7 MB / 463 chunks            | sharded index、GB-TB 規模      |
| Process management  | `pkill -9`                      | systemd / k8s liveness probe   |
| Disk cleanup        | 手動 `ollama rm`                | 自動 retention policy          |
| Cost                | 一次性硬體                      | $/token / day budget alerts    |
| Observability       | `tail log`                      | Prometheus + Grafana / Datadog |
| Failure response    | 自己重啟                        | auto-recover + alert + runbook |

本地數字是「能跑」的證明、production 數字是「能用」的驗證。本地驗證完 architecture 後、production deployment 該重做 load test、不能 assume 線性 scale。

## 跨 framework 不變的設計問題

不管你用 vLLM / TGI / Triton / SGLang / OpenAI API、production 設計都要回答：

1. **Latency vs throughput**：哪個是主要 metric？
2. **Batch strategy**：static / continuous / per-request？
3. **Cost ceiling**：$/day budget 多少？超過怎麼處理？
4. **Storage**：vector DB 規模？update 頻率？
5. **Observability**：哪些 metric 是 alert worthy？
6. **Reliability**：failure mode + graceful degradation 設計
7. **Capacity**：peak + redundancy 需要多少 GPU memory

這 7 個問題回答清楚、framework 選什麼都能跑得起來。

## 何時這篇會過時

**不會過時的部分**：

- 6 個維度（concurrency / latency / cost / storage / observability / reliability）
- Latency-sensitive vs throughput-sensitive 應用的設計差異
- 三類計費單位的取捨
- Metrics / traces / logs 三層觀測
- Graceful degradation 設計

**會變的部分**：

- 具體 inference framework（vLLM / TGI / SGLang 等）的 ranking
- 雲端 API price tier
- 哪些 vector DB 主流

新 framework 出來時、回到 6 維度 framework 問：它在哪個維度有突破？對既有設計問題的答案有沒有改變？通常會發現核心問題沒變、只是工具更熟。

## 跟其他章節的關係

- [hands-on RAG/MCP 資源](/llm/01-local-llm-services/hands-on/rag-mcp-resources/)：本地 baseline 數字、本章的 production extrapolation 起點
- [4.0 RAG](/llm/04-applications/rag-principles/) / [4.1 Tool use](/llm/04-applications/tool-use-principles/) / [4.2 Agent](/llm/04-applications/agent-architecture/)：應用層設計、本章是「應用如何跑」的補完
- [0.5 硬體記憶體預算](/llm/00-foundations/hardware-memory-budget/)：本地單機 perspective、本章對應 multi-machine production
- [1.7 排錯方法論](/llm/01-local-llm-services/troubleshooting/)：本地 trouble-shooting、本章是 production observability 的對照
