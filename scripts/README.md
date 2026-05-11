# Blog Scripts — Local LLM Demos

本資料夾收 blog hands-on 章節對應的可執行 demo。Clone 後按本 README 設定環境就能跑。

## 子資料夾

| 路徑 | 用途 | 對應 blog 文章 |
| ---- | ---- | -------------- |
| `rag-demo/` | RAG 最小實作：embedding + cosine retrieval + Ollama chat | [RAG demo](/content/llm/01-local-llm-services/hands-on/rag-demo.md) |
| `mcp-demo/` | 最小 MCP server：stdio JSON-RPC、暴露 RAG index 當 tool | [MCP demo](/content/llm/01-local-llm-services/hands-on/mcp-demo.md) |
| `permission-demo/` | LLM-mediated file edit、`--dry-run` / `--confirm` / `--auto` 三種 permission gate | [Permission boundary](/content/llm/01-local-llm-services/hands-on/permission-boundary.md) |
| `comfyui-test/` | 用 ComfyUI REST API 跑 SDXL text-to-image | [ComfyUI setup](/content/llm/01-local-llm-services/hands-on/comfyui-setup.md) |
| `mdtools/` | Blog markdown lint + cards validator（Go binary、跟 LLM demo 無關） | — |
| `migrate-relative-links.py` | Blog 內部用、跟 LLM demo 無關 | — |

## 為什麼有些東西不在 repo

下列檔案被 `.gitignore` 排除、要自己 build：

| 檔案 | 為什麼不 commit |
| ---- | --------------- |
| `rag-demo/index.pkl`（3.7 MB） | 衍生資料、可重建（跑 `ingest.py` 重生）、跟 corpus + embedding model 綁定 |
| `__pycache__/` | Python bytecode cache、跟 OS / Python 版本綁定 |
| Ollama / ComfyUI 的 model weights | GB 級、license 限制不能進公開 repo |

詳細的設計取捨見 [4.6 衍生產物管理原理](/content/llm/04-applications/artifact-management.md)。

## Prerequisites（跑任何 demo 之前）

| 工具 | 版本 | 安裝 |
| ---- | ---- | ---- |
| macOS | 14+ | 系統 |
| Homebrew | 4.x | https://brew.sh |
| Python | 3.11+ | 系統內建或 `brew install python` |
| Ollama | 0.20+ | `brew install ollama` |
| ComfyUI（只有 comfyui-test 需要） | main branch | git clone + Python venv、見章節 |

**Python dependency**：純 stdlib（`urllib` / `json` / `pickle` / `subprocess`）、**不需要 `pip install` 任何東西**。

## Setup 步驟（一次性、Ollama 部分）

```bash
# 1. 裝 Ollama + 啟動 daemon
brew install ollama
brew services start ollama

# 2. 驗證 daemon 跑著（應該回 {"version":"0.x.x"}）
curl -s http://localhost:11434/api/version

# 3. 拉 embedding model（RAG / MCP 都要、274 MB）
ollama pull nomic-embed-text

# 4. 拉 chat model（任選、推薦從小開始試）
ollama pull gemma3:1b    # 815 MB、最小驗證
# 或更大：
# ollama pull gemma3:4b  # 3.3 GB、寫 code 任務較穩
# ollama pull qwen3:8b   # 5.2 GB、中文 follow instruction 佳
```

驗證 setup：

```bash
ollama list
# 應該看到 nomic-embed-text + 你拉的 chat model
```

## 跑 RAG demo

```bash
cd /path/to/blog

# 一次性：建 index（每次 content/ 更新後重跑）
python3 scripts/rag-demo/ingest.py
# 預期輸出：Found 71 markdown files... Wrote 463 records to scripts/rag-demo/index.pkl

# 查詢
python3 scripts/rag-demo/query.py "什麼是 KV cache？"
python3 scripts/rag-demo/query.py --show-retrieved --top-k 5 --model gemma3:1b "MCP 跟 function calling 有什麼差別？"
```

## 跑 MCP demo

```bash
# 前提：已跑過 rag-demo/ingest.py、index.pkl 存在
ls scripts/rag-demo/index.pkl

# 跑自動 test client（spawn server + 送 5 個 JSON-RPC request）
python3 scripts/mcp-demo/test_client.py

# 或手動互動（看 protocol wire format）
python3 scripts/mcp-demo/blog_mcp_server.py
# 然後手打：
# {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
```

## 跑 permission demo

```bash
# 備份要試的檔案
cp content/llm/knowledge-cards/token.md /tmp/token-orig.md

# Dry-run（預設、不寫檔）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明"

# Confirm 模式（互動審查）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明" \
  --confirm

# Auto 模式（無確認、危險）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明" \
  --auto

# 還原
cp /tmp/token-orig.md content/llm/knowledge-cards/token.md
```

## 跑 ComfyUI text-to-image demo

需要先裝 ComfyUI + 拉 SDXL model（見 [ComfyUI setup 章節](/content/llm/01-local-llm-services/hands-on/comfyui-setup.md)）。

```bash
# 假設 ComfyUI 已啟動（http://127.0.0.1:8188 跑著）
python3 scripts/comfyui-test/generate.py --steps 15
# 預期：生 1024×1024 PNG 到 /tmp/comfyui-test-output.png、~100 秒
```

## Cleanup

跑完釋放資源（[resource-management 章節](/content/llm/01-local-llm-services/hands-on/resource-management.md) 詳細版）：

```bash
# 釋放 Ollama 載入的 model（保留 daemon）
brew services stop ollama
# 或保留 daemon、只 unload：
# ollama list | tail -n +2 | awk '{print $1}' | xargs -I {} \
#   curl -s http://localhost:11434/api/generate -d "{\"model\":\"{}\",\"keep_alive\":0}"

# kill ComfyUI（如果有跑）
pkill -9 -f "ComfyUI/main.py"

# 清 build artifact（可選、index.pkl 等可重建）
rm -f scripts/rag-demo/index.pkl
find scripts -name __pycache__ -type d -exec rm -rf {} +
```

## Troubleshooting

| 症狀 | 對應章節 |
| ---- | -------- |
| Ollama 沒回應 / curl 失敗 | [Ollama setup § 常見前置設定問題](/content/llm/01-local-llm-services/hands-on/ollama-setup.md) |
| `ollama: command not found` | 同上 |
| 第一次 query 很慢 / cold start | [Resource management § Ollama lifecycle](/content/llm/01-local-llm-services/hands-on/resource-management.md) |
| RAG retrieval 結果不合理 | [4.0 RAG 原理 § Retrieval 失敗的根本原因](/content/llm/04-applications/rag-principles.md) |
| ComfyUI 上傳 prompt 後不執行 | [Troubleshooting 章節](/content/llm/01-local-llm-services/hands-on/troubleshooting.md) |

## 為什麼 demo 都用 stdlib

- 不用 `pip install` 任何東西、cross-machine 跑無摩擦
- HTTP 用 `urllib.request`、序列化用 `json` / `pickle`、subprocess 用 `subprocess`——這些是 stdlib 都有的功能
- 對「LLM API 是 HTTP server」「MCP server 是 stdio JSON-RPC」這類本質、stdlib 就足夠驗證
- 教學用、不是 production：production 用 `requests` / `httpx` / 官方 SDK 較友善、但會 hide 一些 protocol 細節

完整 blog 內容見：<https://tarrragon.github.io/blog/llm/>
