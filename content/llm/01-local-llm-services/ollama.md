---
title: "1.0 Ollama：主流推論伺服器"
date: 2026-05-11
description: "一行 brew 裝完、ollama run 一鍵跑 Gemma 4 MTP、OpenAI 相容 API on localhost:11434"
tags: ["llm", "ollama", "server"]
weight: 0
---

Ollama 是本地 LLM 生態中**學習曲線最低、最值得當第一個工具**的推論伺服器。它的核心承諾是「一行裝完、一行跑模型、自動 expose OpenAI 相容 API」；底層用 llama.cpp 當推論引擎，但把 GGUF 格式、量化選擇、KV cache 等細節都包好，使用者只看到 model tag 跟 CLI 指令。

對主要目標是「在 VS Code 接本地 LLM 寫 code」的讀者來說，Ollama 多半是唯一需要的伺服器層。本章把它的安裝、模型管理、API 使用、常見坑都走過一遍。

## 本章目標

讀完本章後，你應該能：

1. 裝好 Ollama 並驗證它正在跑。
2. 拉一個模型並用 CLI 對話。
3. 用 curl 驗證 OpenAI 相容 API 在 11434 正常回應。
4. 知道 model tag 命名規則、怎麼選 Gemma 4 MTP 版本。
5. 處理常見坑：port 撞、記憶體不足、模型載入慢、cache 在哪。

## 安裝：一行就完事

最快的安裝方式是用 Homebrew：

```bash
brew install ollama
```

裝完後啟動伺服器：

```bash
ollama serve
```

`ollama serve` 是常駐 process，會一直跑直到你 Ctrl+C 或關 terminal。日常使用建議放背景：

```bash
ollama serve &
```

或裝成 macOS service（重開機自動啟動）：

```bash
brew services start ollama
```

`brew services` 會把 Ollama 註冊成 launchd service，背景跑、log 進 `/opt/homebrew/var/log/ollama.log`（Apple Silicon Mac）。多數使用者建議用這種方式，省去每次重開機要手動啟動。

驗證它在跑：

```bash
curl http://localhost:11434/api/version
```

應該回類似 `{"version":"0.23.1"}` 的 JSON。

## 拉第一個模型

Ollama 的模型管理用 `ollama pull` 跟 `ollama run`：

```bash
# 只下載、不啟動對話
ollama pull gemma3:4b

# 下載（如果還沒有）+ 啟動對話 session
ollama run gemma3:4b
```

`ollama run` 進入互動 REPL 後可以直接對話：

```text
>>> 寫一個 Python function 計算 fibonacci
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
...
>>> /bye
```

`/bye` 退出 REPL。

列出已下載的模型：

```bash
ollama list
```

刪除模型釋出空間：

```bash
ollama rm gemma3:4b
```

模型權重存放路徑（macOS）：`~/.ollama/models/`。大模型（30B+）一個檔案可能 18 ~ 30GB，記得監控 SSD 剩餘空間。

## Model tag 命名規則

Ollama 的 model tag 形式是 `family:size-variant-quantization`：

| 範例                           | 拆解                                            |
| ------------------------------ | ----------------------------------------------- |
| `gemma3:4b`                    | Gemma 3 系列、4B 參數、預設量化（通常 Q4_K_M）  |
| `gemma3:27b-instruct-q5_K_M`   | Gemma 3、27B、instruct-tuned、Q5_K_M 量化       |
| `gemma4:31b-coding-mtp-bf16`   | Gemma 4、31B、coding 特化、含 MTP drafter、bf16 |
| `qwen3-coder:30b`              | Qwen3-Coder、30B 參數、預設量化                 |
| `llama3.3:70b-instruct-q4_K_M` | Llama 3.3、70B、instruct、Q4_K_M                |

完整 tag 清單在 [ollama.com/library](https://ollama.com/library)。對寫 code 場景的推薦選擇，詳見 [1.4 模型選型優先順序](/llm/01-local-llm-services/model-selection-priority/)。

## Gemma 4 MTP：一鍵加速

Ollama v0.23.1（2026/5/7 釋出）加入 Gemma 4 的 MTP（Multi-Token Prediction）一鍵支援。MTP 是 [speculative decoding](/llm/00-foundations/why-llm-feels-slow/) 的具體實作，coding 任務官方數據 2 ~ 3 倍加速。詳細原理見 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)。

啟用方式只需要 pull 對應 model tag：

```bash
ollama run gemma4:31b-coding-mtp-bf16
```

這個 tag 內含 target model（31B）跟 drafter（Google 釋出的官方小模型）。Ollama 自動把兩個 model 載入記憶體、在推論時並行驗證。記憶體佔用約 18GB（drafter 約 1GB、其餘為 target），需要 32GB+ Mac 才能順暢跑。

陷阱：

1. **bf16 不是「最大量化」**。bf16 在 Gemma 4 31B 上的記憶體佔用是 60GB+，跑不動。`gemma4:31b-coding-mtp-bf16` 的 `bf16` 標記指的是 drafter 用 bf16，target 內部有量化。實際佔用 18GB 左右。
2. **MTP 對所有任務都加速嗎？** 不是。coding 任務（pattern 預測度高）加速最明顯，純創意寫作、隨機字串生成的加速幅度可能只有 1.5x。
3. **drafter 失敗時不影響正確性**。speculative decoding 的設計保證：drafter 猜錯時 target 會拒絕，最終輸出跟「不用 drafter 直接生成」一致。drafter 只影響速度，不影響品質。

## OpenAI 相容 API

Ollama 預設聽 `localhost:11434`，提供兩套 API：

1. **OpenAI 相容**：`http://localhost:11434/v1/...`，跟 OpenAI 同樣的 endpoint 形狀。
2. **Ollama 原生**：`http://localhost:11434/api/...`，較豐富，包含 model 管理。

寫 code 場景多半用 OpenAI 相容那一套，因為大多數 IDE plugin 與 CLI 工具預設講這套。詳見 [0.3 OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)。

用 curl 驗證 chat completions（非 streaming）：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:31b-coding-mtp-bf16",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

驗證 streaming：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:31b-coding-mtp-bf16",
    "messages": [{"role": "user", "content": "Count from 1 to 5."}],
    "stream": true
  }'
```

Streaming 會看到一連串 `data: {...}` 行，每行是一個 token chunk。

Ollama 原生 API（`/api/generate`）支援更細的參數控制，例如指定 `num_predict`（最大生成 token 數）、`temperature`、`top_p`、`stop` 等。一般使用者用不到，IDE plugin 內部會處理。

## 常見坑

### Port 11434 被佔用

啟動 `ollama serve` 報 `address already in use`，通常是另一個 Ollama instance 還在跑。處理方式：

```bash
# 找出佔用 11434 的 process
lsof -i :11434

# 如果是舊的 ollama，kill 它
pkill -f "ollama serve"

# 重新啟動
ollama serve &
```

或者改 port：

```bash
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

改 port 後 IDE plugin 的 `apiBase` 也要對應改。

### 記憶體不足、模型崩潰

跑大模型時系統可能 swap 嚴重、整台 Mac 變慢，甚至 Ollama 自己 crash。判讀方式：

```bash
# 看 Ollama 載入的 model 與記憶體佔用
ollama ps
```

如果你的 model 比 Mac 記憶體預算大（見 [0.5 記憶體預算](/llm/00-foundations/hardware-memory-budget/)），請降級到較小模型或較激進量化。

### 模型載入很慢

`ollama run` 第一次跑某個 model 時，需要 30 ~ 60 秒把 18GB 權重從 SSD 載入記憶體。後續對話會快得多，因為 Ollama 把 model 留在記憶體（直到 `keep_alive` timeout，預設 5 分鐘）。

長時間不用會被 unload 釋放記憶體，下次再用又要等載入。如果要避免：

```bash
# 啟動時設定 keep_alive 為 -1（永久保留）
OLLAMA_KEEP_ALIVE=-1 ollama serve
```

但這會持續佔用記憶體；只有「整天會頻繁用」的場景才開。

### Model cache 太大佔滿 SSD

`~/.ollama/models/` 累積會很快超過 100GB。清理方式：

```bash
# 列出所有 model 大小
ollama list

# 刪除不用的
ollama rm <model-tag>
```

別手動 `rm -rf ~/.ollama/models/`，會破壞 model registry metadata，下次 `ollama list` 會出錯。

### 對外暴露

預設 Ollama 只聽 `127.0.0.1`，不接受區網連線。如果你要從另一台機器（例如桌機跑 server、筆電當 client）連：

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

但這會把本地 LLM 暴露在 LAN 上，任何同網路裝置都能用。家用網路通常還好，公共 Wi-Fi 千萬不要這樣設。要進一步加防火牆規則或用 SSH tunnel 比較安全。

## 升級與版本管理

升級 Ollama：

```bash
brew upgrade ollama
brew services restart ollama
```

升級前建議先看 release notes（`github.com/ollama/ollama/releases`）。本地 LLM 工具更新節奏快，每兩三週可能有新版加新功能或修嚴重 bug。但更新後新 model tag 可能要重新 pull，舊 model 偶爾會被廢棄。

## 跟其他伺服器並存

Ollama 跟 LM Studio、llama.cpp 可以同時在同一台 Mac 跑，port 不同就不會撞：

| 伺服器    | 預設 port |
| --------- | --------- |
| Ollama    | 11434     |
| LM Studio | 1234      |
| llama.cpp | 8080      |
| oMLX      | 8000      |

並存的好處是「主力穩定跑 Ollama、實驗模型用 LM Studio」。Continue.dev 等介面層可以同時設多個 model，UI 上切換。

## 小結

Ollama 是 2026 年 5 月本地 LLM 生態的預設選擇：學習曲線最低、Gemma 4 MTP 一鍵支援、OpenAI 相容 API 出廠就有、生態最成熟。多數讀者只需要這一個伺服器。

下一章可選擇：

- 想對比 GUI 派的選擇：[1.1 LM Studio](/llm/01-local-llm-services/lm-studio/)
- 想了解底層 / 為何不直接用 llama.cpp：[1.2 llama.cpp](/llm/01-local-llm-services/llama-cpp/)
- 直接進入 VS Code 整合：[1.3 VS Code + Continue.dev](/llm/01-local-llm-services/vscode-continue-integration/)
