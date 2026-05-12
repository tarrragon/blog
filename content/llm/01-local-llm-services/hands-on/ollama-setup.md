---
title: "Hands-on：安裝 Ollama + 拉第一個 Gemma 模型"
date: 2026-05-11
description: "brew install ollama、launchd service、ollama pull、curl 驗證 OpenAI 相容 API"
tags: ["llm", "hands-on", "ollama", "gemma"]
weight: 0
---

本篇紀錄在 Apple Silicon Mac 上裝 Ollama 並拉一個小模型驗證的完整流程。指令在 macOS 14 (Sonoma) / Homebrew 提供的環境下驗證。

> **驗證日期**：2026-05-11
> **Ollama 版本**：0.23.2
> **示範模型**：`gemma3:1b`（約 815 MB、選最小可運行的 Gemma 變體當驗證對象）

## 前置設定

| 項目          | 檢查指令                  | 預期                               |
| ------------- | ------------------------- | ---------------------------------- |
| macOS 版本    | `sw_vers -productVersion` | 14.x 或更新                        |
| Apple Silicon | `uname -m`                | `arm64`                            |
| Homebrew      | `brew --version`          | 4.x（任何近期版）                  |
| 磁碟空間      | `df -h ~`                 | 至少 3 GB 剩餘給 runtime + 1B 模型 |
| port 11434    | `lsof -i :11434`          | 無輸出（port 沒被佔）              |

選 1B 模型只是為了驗證流程、能力很弱、實際寫 code 場景請用 14B / 31B 級。模型大小跟記憶體 / 磁碟對應關係見 [0.5 Apple Silicon 記憶體預算](/llm/00-foundations/hardware-memory-budget/)。

## 安裝 Ollama

用 Homebrew 安裝、是 macOS 上最直接的路徑：

```bash
brew install ollama
```

執行時間在 broadband 大約 30 秒到 2 分鐘、視 dependency cache 是否已有（Ollama 依賴 mlx-c 等 Apple Silicon 加速函式庫、首次裝較久）。

裝完看到的 caveat 訊息：

```text
To start ollama now and restart at login:
  brew services start ollama
Or, if you don't want/need a background service you can just run:
  OLLAMA_FLASH_ATTENTION="1" OLLAMA_KV_CACHE_TYPE="q8_0" /opt/homebrew/opt/ollama/bin/ollama serve
```

兩種啟動模式：

- **launchd service**（推薦日常用）：開機自動啟動、跑在背景。
- **前景手動跑**：terminal 開著、關掉就停。

驗證 binary 路徑：

```bash
which ollama
# 應該回 /opt/homebrew/bin/ollama
```

## 啟動 Ollama Service

選 launchd service 模式：

```bash
brew services start ollama
```

預期輸出：

```text
==> Successfully started `ollama` (label: homebrew.mxcl.ollama)
```

這個動作做兩件事：

1. 註冊一個 launchd plist（macOS 開機自啟動 / 背景服務的設定檔、見 [launchd-service 卡片](/llm/knowledge-cards/launchd-service/)）到 `~/Library/LaunchAgents/homebrew.mxcl.ollama.plist`。
2. 立刻啟動 ollama serve、之後重開機自動啟動。

驗證 server 真的在跑：

```bash
curl -s http://localhost:11434/api/version
```

預期回：

```json
{"version":"0.23.2"}
```

看到這個 JSON 就證明三件事：Ollama daemon 跑了、port 11434 通了、API 結構正確。

## 拉第一個模型

Ollama 用 `ollama pull` 從官方 registry 下載模型：

```bash
ollama pull gemma3:1b
```

Gemma 3 1B 約 815 MB、broadband 約 1-2 分鐘下載。下載過程顯示多階段：

```text
pulling 7cd4618c1faf: 100% ▕██████████████████▏ 815 MB
pulling e0a42594d802: 100% ▕██████████████████▏  358 B
pulling dd084c7d92a3: 100% ▕██████████████████▏  8.4 KB
pulling 3116c5225075: 100% ▕██████████████████▏   77 B
pulling 120007c81bf8: 100% ▕██████████████████▏  492 B
verifying sha256 digest
writing manifest
success
```

幾個 hash blob 分別是：模型權重（最大那個）、tokenizer、template、license metadata 等。Ollama 把這些統一管理、放在 `~/.ollama/models/`。

驗證模型已下載：

```bash
ollama list
```

預期：

```text
NAME         ID              SIZE      MODIFIED
gemma3:1b    8648f39daa8f    815 MB    35 seconds ago
```

## 驗證 OpenAI 相容 API

OpenAI 相容 API 是下游所有工具（IDE plugin、RAG pipeline、MCP server、[Continue.dev](/llm/01-local-llm-services/vscode-continue-integration/) 等）依賴的介面 contract、驗證它能正常回應、整個 stack 才走得通：

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:1b",
    "messages": [{"role":"user","content":"Reply in one short sentence: what is 2+2?"}],
    "stream": false
  }'
```

預期回 JSON、`choices[0].message.content` 是模型回答（如 `"2 + 2 = 4"`）。看到合理回答就證明：

1. Ollama 跟模型權重對接好。
2. OpenAI 相容 API 格式正常（IDE plugin 可以接）。
3. 推論流程整條通。

常見的失敗回應跟下一步：

- **`{"error":"model 'gemma3:1b' not found, try pulling it first"}`**：先跑 `ollama pull gemma3:1b`、確認 `ollama list` 看到該 tag。
- **`curl: (7) Failed to connect to localhost port 11434: Connection refused`**：server 沒在跑、回 `brew services list` 看 status、若是 stopped 跑 `brew services start ollama`。
- **`{"error":"json: cannot unmarshal ..."}`**：請求格式錯（例如 messages 寫成 string 不是 array）、檢查 JSON body。
- **連得上但長時間沒回應**：第一次載入大 model 需要 30 ~ 60 秒、看 `~/.ollama/logs/server.log` 確認是否還在 loading。

用內建 CLI 互動模式也行：

```bash
ollama run gemma3:1b
```

進入 REPL、可以打字對話。`/bye` 離開。

第一次跑 `ollama run` 會把模型載入記憶體（1B 模型大約 1-2 秒）、之後對話延遲低。如果幾分鐘沒用、模型會被 unload 釋放記憶體、下次 run 又要等載入。控制行為的環境變數是 `OLLAMA_KEEP_ALIVE`（預設 5 分鐘）。

## 常見前置設定問題

### Port 11434 被佔用

```bash
lsof -i :11434
```

若已有 process 占用、可能是先前手動跑過 `ollama serve` 沒關。kill 後再 start service：

```bash
pkill -f "ollama serve"
brew services restart ollama
```

### `ollama: command not found`（裝完還是找不到）

Homebrew 在 Apple Silicon 預設裝到 `/opt/homebrew/bin`、shell PATH 應該已含。若沒含：

```bash
echo $PATH | tr ':' '\n' | grep homebrew
# 若沒看到 /opt/homebrew/bin、要加進 ~/.zshrc：
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Server 啟動但 curl 失敗

```bash
brew services list | grep ollama
```

若 status 不是 `started`、看 log：

```bash
tail -50 /opt/homebrew/var/log/ollama.log
```

常見原因：port 衝突、權限問題、上次 crash 沒清乾淨。

完整排錯流程見 [1.7 排錯方法論](/llm/01-local-llm-services/troubleshooting/)。

## 之後想做的事

- **接 VS Code**：見 [1.3 VS Code + Continue.dev 整合](/llm/01-local-llm-services/vscode-continue-integration/)。設定 `apiBase: http://localhost:11434` 就能用。
- **跑更大模型**：32GB+ Mac 推薦 `gemma4:31b-coding-mtp-bf16`（18 GB）。模型選擇見 [1.4 模型選型優先順序](/llm/01-local-llm-services/model-selection-priority/)。
- **加 embedding**：codebase 索引要 embedding 模型：`ollama pull nomic-embed-text`（274 MB）、見 [4.0 RAG 原理](/llm/04-applications/rag-principles/)。

## 升級 / 移除

升級：

```bash
brew upgrade ollama
brew services restart ollama
```

完整移除：

```bash
brew services stop ollama
brew uninstall ollama
rm -rf ~/.ollama  # 清模型 cache（可選）
```

## 何時這篇會過時

- `brew install ollama` 安裝方式跟 OpenAI 相容 API 形狀短期內不會變（生態都依賴）。
- `gemma3:1b` 這個具體 tag 預期會被新模型取代、但「拉一個小模型驗證流程」的方法不變。
- launchd service 機制是 macOS 系統 API、不會 deprecate。

讀的時候若 `brew install` 跑失敗、查 Ollama GitHub release notes；其餘驗證步驟結構通用。
