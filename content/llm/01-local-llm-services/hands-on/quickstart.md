---
title: "Hands-on Quickstart：clone repo 後跑通所有 demo"
date: 2026-05-12
description: "4 步驟跑通 RAG / MCP / permission demo 的 setup 跟驗證指令、整合 hands-on 系列所有章節的 prerequisite"
tags: ["llm", "hands-on", "quickstart", "setup"]
weight: 0
---

本篇是 hands-on 系列的**導讀**——把分散在 `ollama-setup` / `rag-demo` / `mcp-demo` / `permission-boundary` 各章節的 setup 步驟整合成一條最短路徑、讓 clone repo 的人能在 15 分鐘內跑通所有 demo（[RAG](/llm/knowledge-cards/rag/)、[MCP](/llm/knowledge-cards/mcp/)、權限邊界三個 demo）。

每篇 hands-on 文章 focus 在「為什麼這樣設計」、本篇 focus 在「按順序跑通」。讀完想懂原理再進對應章節讀。

> **驗證日期**：2026-05-12
> **環境**：macOS 14+、Apple Silicon、Ollama 0.23.2、Python 3.11+
> **總時間**：~15 分鐘（含 model 下載）
> **磁碟需求**：~5 GB（Ollama 200 MB + nomic-embed-text 274 MB + gemma3:1b 815 MB + room for index）

## 適合誰讀

| 你是 | 本篇對你 |
| ---- | -------- |
| 剛 clone 我的 blog repo、想跑 demo 試試看 | **從本篇開始**、按步驟做 |
| 想懂某個 demo 的設計取捨 | 跑通後再進 [RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/) / [MCP demo](/llm/01-local-llm-services/hands-on/mcp-demo/) / [permission-boundary](/llm/01-local-llm-services/hands-on/permission-boundary/) |
| 想懂 Ollama / ComfyUI 安裝細節 | [Ollama setup](/llm/01-local-llm-services/hands-on/ollama-setup/) / [ComfyUI setup](/llm/01-local-llm-services/hands-on/comfyui-setup/) |
| 想看 production 怎麼想資源評估 | [4.5 Production resource planning](/llm/04-applications/production-resource-planning/) |

## 為什麼不是「pre-built、clone 就能跑」

衍生產物（`index.pkl`、`__pycache__/`、Ollama model weights）刻意**不進 git**、原因見 [4.6 衍生產物管理原理](/llm/04-applications/artifact-management/)。所以 clone repo 後需要：

1. 裝 Ollama daemon + 拉 model（一次性）
2. 跑 `ingest.py` 建 RAG index（corpus 變動時重跑）
3. 之後 demo 就能用

本篇是這個流程的 step-by-step。

## Step 1：裝 Ollama + 啟動 daemon

```bash
brew install ollama
brew services start ollama
```

驗證：

```bash
curl -s http://localhost:11434/api/version
# {"version":"0.x.x"}
```

詳細安裝跟 troubleshooting 見 [Ollama setup 章節](/llm/01-local-llm-services/hands-on/ollama-setup/)。

## Step 2：拉兩個 model

```bash
# Embedding model（RAG / MCP 都要、274 MB）
ollama pull nomic-embed-text

# Chat model（推薦從 1B 開始驗證、之後可換大）
ollama pull gemma3:1b
```

驗證：

```bash
ollama list
# NAME                       SIZE      MODIFIED
# gemma3:1b                  815 MB    ...
# nomic-embed-text:latest    274 MB    ...
```

選 chat model 大小的取捨見 [1.4 模型選型優先順序](/llm/01-local-llm-services/model-selection-priority/)。本 quickstart 用 1B 主要驗證流程跑通、實際應用要 4B / 8B 起跳才有 follow instruction 能力（見 [instruction-following-test](/llm/01-local-llm-services/hands-on/instruction-following-test/)）。本系列預設用 [instruction-tuned model](/llm/knowledge-cards/instruction-tuned/) 變體（tag 含 `:Xb` 不含 `-base`）、適合對話 / 寫 code。

## Step 3：建 RAG index

```bash
cd /path/to/blog
python3 scripts/rag-demo/ingest.py
```

預期輸出：

```text
Found 71 markdown files under content/llm
  [10/71] 86 chunks in 4.5s
  ...
Wrote 463 records to scripts/rag-demo/index.pkl (22.3s)
```

實際數字看你的 blog content 量。Index file 在 `scripts/rag-demo/index.pkl`、3-50 MB 不等。

詳細的 chunking 策略、embedding 設計、為什麼 pickle、見 [RAG demo 章節](/llm/01-local-llm-services/hands-on/rag-demo/)。

## Step 4：跑 demo

完成 step 1-3 後、四個 demo 都能跑了：

### RAG demo（語意搜尋 + LLM 回答）

```bash
python3 scripts/rag-demo/query.py --show-retrieved "你的問題"
```

例：

```bash
python3 scripts/rag-demo/query.py --show-retrieved "什麼是 MCP？"
```

預期看到 retrieved chunks（含相似度跟來源 path）+ LLM 用這些 context 生的答案。

### MCP demo（stdio JSON-RPC server）

```bash
python3 scripts/mcp-demo/test_client.py
```

預期看到 5 個階段的 JSON-RPC 對話：initialize / tools/list / tools/call (search_blog) / tools/call (read_chunk) / error。

### Permission boundary demo（LLM-mediated file edit）

```bash
# 備份要試的檔案
cp content/llm/knowledge-cards/token.md /tmp/token-orig.md

# Dry-run（預設、不寫檔、印 diff）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明"

# 還原（如果剛剛沒用 dry-run）
cp /tmp/token-orig.md content/llm/knowledge-cards/token.md
```

詳細的 `--dry-run` / `--confirm` / `--auto` 三種 mode 取捨見 [Permission boundary 章節](/llm/01-local-llm-services/hands-on/permission-boundary/)。

## Step 5（可選）：ComfyUI text-to-image demo

需要額外裝 ComfyUI + 拉 SDXL model（~10 GB 磁碟）、流程獨立：

```bash
# 跟 step 1 平行的軌道、見 ComfyUI setup 章節
cd ~/Projects
git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# 下載 SDXL base：~/Projects/ComfyUI/models/checkpoints/
# 見 ComfyUI setup 章節指令
```

啟動 + 跑 generation：

```bash
cd ~/Projects/ComfyUI && source venv/bin/activate && nohup python main.py > /tmp/comfyui.log 2>&1 &
# 等 server ready
until curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8188/ | grep -q 200; do sleep 2; done

# 跑 generation（用 repo 內的 script）
cd /path/to/blog
python3 scripts/comfyui-test/generate.py --steps 15
```

詳細裝法 + workflow JSON 解讀見 [ComfyUI setup 章節](/llm/01-local-llm-services/hands-on/comfyui-setup/)。

## Cleanup（完事釋放資源）

```bash
# 停 Ollama daemon
brew services stop ollama

# kill ComfyUI（如果有跑）
pkill -9 -f "ComfyUI/main.py"

# 清 build artifact（可選、可重建）
rm -f scripts/rag-demo/index.pkl
find scripts -name __pycache__ -type d -exec rm -rf {} +
```

詳細的 resource lifecycle 跟 cleanup idiom 見 [Resource management 章節](/llm/01-local-llm-services/hands-on/resource-management/)。

## 跑通後該往哪讀

| 想懂什麼 | 讀哪 |
| -------- | ---- |
| 「RAG 為什麼 retrieval 對 / generation 弱」| [RAG demo](/llm/01-local-llm-services/hands-on/rag-demo/) |
| 「MCP wire protocol 細節」 | [MCP demo](/llm/01-local-llm-services/hands-on/mcp-demo/) |
| 「為什麼 LLM 寫 `rm -rf` 不會真的執行」 | [Permission boundary](/llm/01-local-llm-services/hands-on/permission-boundary/) |
| 「不同 model 在 instruction following 上的差距」 | [Instruction following test](/llm/01-local-llm-services/hands-on/instruction-following-test/) |
| 「跑 demo 占多少 RAM、怎麼釋放」 | [Resource management](/llm/01-local-llm-services/hands-on/resource-management/) + [RAG/MCP 資源 footprint](/llm/01-local-llm-services/hands-on/rag-mcp-resources/) |
| 「production 部署該怎麼想」 | [4.5 Production resource planning](/llm/04-applications/production-resource-planning/) |
| 「什麼該進 git、什麼不該」 | [4.6 衍生產物管理原理](/llm/04-applications/artifact-management/) |

## 跑不過時

| 症狀 | 對應章節 |
| ---- | -------- |
| `ollama: command not found` | [Ollama setup § 常見前置設定問題](/llm/01-local-llm-services/hands-on/ollama-setup/) |
| `curl http://localhost:11434/api/version` 沒回應 | 同上 |
| `python3 ingest.py` 報 HTTP error | 確認 Ollama daemon 跑著、nomic-embed-text 已 pull |
| RAG retrieval 結果都不相關 | [4.0 RAG § Retrieval 失敗的根本原因](/llm/04-applications/rag-principles/) |
| MCP test_client 卡住 | [MCP demo § subprocess 跟 bufsize](/llm/01-local-llm-services/hands-on/mcp-demo/) |
| 一切都不對 | [1.7 排錯方法論](/llm/01-local-llm-services/troubleshooting/) |

## 何時這篇會過時

**會變的部分**：

- `brew install ollama` 流程（macOS 跟 brew 演化）
- `ollama pull` 的具體 model tag（model 會新陳代謝）
- Python 版本相容性（3.11 → 3.14 各有 quirk）

**不會過時的部分**：

- 4 步驟的順序（裝 daemon → 拉 model → 建 index → 跑 demo）是 RAG / MCP / 任何 LLM 應用的通用 setup pattern
- 衍生產物（index、cache）不進 git 的設計取捨
- Cleanup 步驟跟釋放邏輯

跑指令時報錯先看 step 對應章節的 troubleshooting section、再 Google 或開 issue。
