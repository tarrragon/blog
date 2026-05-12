---
title: "1.0 Ollama：主流推論伺服器"
date: 2026-05-11
description: "一行 brew 裝完、ollama run 一鍵跑 Gemma 4 MTP、OpenAI 相容 API on localhost:11434"
tags: ["llm", "ollama", "server"]
weight: 0
---

Ollama 是本地 LLM 生態的**主流推論伺服器**、承擔三個責任：模型管理（拉、存、列、刪）、推論執行（呼叫 [llama.cpp](/llm/01-local-llm-services/llama-cpp/) backend）、API 暴露（預設 [`localhost:11434`](/llm/knowledge-cards/port-and-localhost/) 上的 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 與原生 API）。它的設計取捨偏向「拿來就跑」、把 [GGUF 格式](/llm/knowledge-cards/gguf/)、[量化](/llm/knowledge-cards/quantization/)、[KV cache](/llm/knowledge-cards/kv-cache/) 等底層細節都包進 CLI、使用者面對的只有 [model tag](/llm/knowledge-cards/model-tag/) 跟幾個指令。

對「在 VS Code 接本地 LLM 寫 code」這條最短路徑、Ollama 多半是唯一需要的伺服器層。本章先給 5 分鐘可跑通的最短路徑、再展開日常使用所需的模型管理跟 API 細節、最後才進階主題（背景常駐、MTP 加速、安全暴露、版本升級）。已經把 Ollama 跑起來的讀者可以直接跳到[日常使用](#日常使用模型管理與-api-形狀)或[排錯](#排錯快速判讀)。

## 本章目標

讀完本章後、你應該能：

1. 裝好 Ollama 並驗證它正在跑。
2. 用 CLI 拉一個模型並開始對話。
3. 用 curl 驗證 OpenAI 相容 API 在 11434 正常回應。
4. 看懂 model tag 命名規則、選對 Gemma 4 MTP 版本。
5. 排查 port 撞、記憶體不足、模型載入慢、cache 過大等情境。

## 最短路徑：5 分鐘把 Ollama 跑起來

最短路徑的設計目標是「裝、跑、驗證三步、其他細節留到日常使用段」。三個指令用到的 macOS 工具分別是 [Homebrew 套件管理器](/llm/knowledge-cards/homebrew/)（`brew install`）跟 [shell 前景 process](/llm/knowledge-cards/shell-background-process/)（`ollama serve` 預設前景跑、`Ctrl+C` 結束）。

```bash
# 1. 安裝
brew install ollama

# 2. 啟動 server（前景跑、Ctrl+C 結束）
ollama serve

# 3. 在另一個 terminal 拉一個小模型驗證
ollama run gemma3:1b
```

第三步首次執行會下載權重（約 815 MB、頻寬足夠的話 1 ~ 3 分鐘）、下載完自動進入 REPL：

```text
>>> 寫一個 Python function 計算 fibonacci
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
>>> /bye
```

驗證 server 正常聽 11434：

```bash
curl http://localhost:11434/api/version
# 回 {"version":"0.23.x"}
```

驗證 OpenAI 相容 API 可以做 chat completion：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:1b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

回應 JSON 包含 `choices[0].message.content`、最短路徑就完成。實際寫 code 用的模型大小通常是 14B / 31B 級、選型詳見 [1.4 模型選型優先順序](/llm/01-local-llm-services/model-selection-priority/)；完整安裝紀錄含 [launchd service](/llm/knowledge-cards/launchd-service/) 設定見 [Hands-on：Ollama 安裝](/llm/01-local-llm-services/hands-on/ollama-setup/)。

## 日常使用：模型管理與 API 形狀

### 模型管理指令

Ollama 用四個指令覆蓋日常模型管理。每個指令承擔一個語意責任：

| 指令                | 責任                             | 何時使用                      |
| ------------------- | -------------------------------- | ----------------------------- |
| `ollama pull <tag>` | 只下載權重、不啟動對話           | CI / 自動化、先下載再離線使用 |
| `ollama run <tag>`  | 下載（若還沒）+ 啟動對話 REPL    | 互動驗證、快速試模型          |
| `ollama list`       | 列出已下載模型與大小             | 檢查磁碟用量、確認模型存在    |
| `ollama rm <tag>`   | 刪除模型權重與 registry metadata | 釋出 SSD 空間                 |

模型權重存在 `~/.ollama/models/`、單一大模型（30B+）可能佔 18 ~ 30 GB、累積超過 100 GB 很常見。清理路徑統一用 `ollama rm`、Ollama 會同步更新 registry metadata、後續 `ollama list` 與 `ollama pull` 才能正確判斷既存模型狀態。

### Model tag 命名規則

[Model tag](/llm/knowledge-cards/model-tag/) 是 Ollama 的模型定位符、形式為 `family:size-variant-quantization`。同一個 model family 可能有十幾個 tag、對應不同參數量、訓練變體跟量化等級。

| 範例                           | 拆解                                            |
| ------------------------------ | ----------------------------------------------- |
| `gemma4:e4b`                   | Gemma 4、E4B（edge dense）、預設量化            |
| `gemma4:31b-instruct-q5_K_M`   | Gemma 4、31B、instruct-tuned、Q5_K_M 量化       |
| `gemma4:31b-coding-mtp-bf16`   | Gemma 4、31B、coding 特化、含 MTP drafter、bf16 |
| `qwen3-coder:30b`              | Qwen3-Coder、30B 參數、預設量化                 |
| `llama3.3:70b-instruct-q4_K_M` | Llama 3.3、70B、instruct、Q4_K_M                |

選 tag 時的兩個判讀重點：variant（`instruct` / `coding` 等用途特化、影響回應風格）、quantization（量化等級、影響記憶體佔用與品質、見 [1.2 llama.cpp 的量化標籤對照](/llm/01-local-llm-services/llama-cpp/#gguf-格式與量化標籤)）。完整 tag 清單在 [ollama.com/library](https://ollama.com/library)。寫 code 場景的推薦選擇詳見 [1.4 模型選型](/llm/01-local-llm-services/model-selection-priority/)。

### 兩套 API：選哪一套

Ollama 在 11434 同時提供兩套 API、用途互補：

| 路徑前綴 | 目的                            | 適合誰                                                            |
| -------- | ------------------------------- | ----------------------------------------------------------------- |
| `/v1/…`  | OpenAI 相容、用 `messages` 結構 | IDE plugin（Continue.dev 等）、CLI 工具、想無痛切換 cloud / local |
| `/api/…` | Ollama 原生、支援模型管理       | 想動態切換模型、寫 model 管理腳本                                 |

寫 code 場景多半用 `/v1/…`、因為 IDE plugin 預設講這套形狀。詳細協定背景見 [0.3 OpenAI 相容 API](/llm/00-foundations/openai-compatible-api/)。

驗證 streaming 回應：

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:1b",
    "messages": [{"role": "user", "content": "Count 1 to 5"}],
    "stream": true
  }'
```

Streaming 回應是一連串 `data: {...}` 行、每行一個 token chunk。Ollama 原生 `/api/generate` 還支援 `num_predict`、`temperature`、`stop` 等細項、IDE plugin 內部會自行轉換、終端使用者通常用不到。

## 進階主題（按需閱讀）

進階段的特色是「沒有它最短路徑仍能跑、但搞懂後體驗大幅提升」。最短路徑只想跑通的讀者可以先跳到[排錯](#排錯快速判讀)、需要時再回來。

### 背景常駐：launchd service

`ollama serve` 預設[在前景跑](/llm/knowledge-cards/shell-background-process/)、terminal 關掉就停。日常使用建議讓 Ollama 開機自動啟動、用 macOS 的 [launchd service](/llm/knowledge-cards/launchd-service/) 機制：

```bash
brew services start ollama
```

這個指令做兩件事、決定 Ollama 之後的行為：

1. 寫一個 launchd plist 到 `~/Library/LaunchAgents/homebrew.mxcl.ollama.plist`
2. 立刻啟動 ollama serve、之後重開機自動拉起

launchd 是 macOS 原生的服務管理機制、把 process 註冊成 daemon / agent、由系統負責生命週期。`brew services` 是 [Homebrew](/llm/knowledge-cards/homebrew/) 對 launchd 的封裝、把 plist 模板跟啟動指令簡化成一行。Log 統一寫到 `/opt/homebrew/var/log/ollama.log`（Apple Silicon Mac）、出問題第一步先看這個檔。

對應的服務管理指令：

```bash
brew services stop ollama      # 停掉、保留 plist
brew services restart ollama   # 升級後重啟
```

完整 plist 內容與 log 範例見 [Hands-on：Ollama 安裝](/llm/01-local-llm-services/hands-on/ollama-setup/)。

### Gemma 4 MTP 一鍵加速

[Multi-Token Prediction（MTP）](/llm/knowledge-cards/mtp/) 是 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 的具體實作、用一個小 [drafter](/llm/knowledge-cards/drafter-model/) 預測多個 token、再由 target model 驗證、coding 任務有 2 ~ 3 倍加速。Ollama v0.23.1（2026/5/7 釋出）內建 Gemma 4 的 MTP 一鍵支援、啟用方式只需要 pull 對應 model tag：

```bash
ollama run gemma4:31b-coding-mtp-bf16
```

這個 tag 內含 target model（31B）跟 drafter（Google 釋出的官方小模型）、Ollama 自動把兩個 model 載入記憶體、推論時並行驗證。記憶體佔用約 18 GB（drafter 約 1 GB、其餘為 target）、適合 32GB+ Mac。詳細原理見 [0.4 MLX / MTP / oMLX](/llm/00-foundations/mlx-mtp-omlx/)。

判讀 MTP tag 時的三個重點：

1. **Tag 裡的 `bf16` 描述的是 drafter 精度**。Target model 內部已套用量化、實際佔用約 18 GB、跟「整個 31B 用 bf16 跑、要 60+ GB」是兩件事。
2. **加速幅度跟任務 pattern 預測度成正比**。Coding（pattern 強）2 ~ 3 倍、純創意寫作或隨機字串生成大約 1.5 倍。
3. **品質由 target model 保證**。Drafter 猜錯時 target 會拒絕該預測、最終輸出跟「直接由 target 生成」一致、drafter 只影響速度。

### 模型常駐：keep_alive

`ollama run` 第一次跑某個 model 時、需要 30 ~ 60 秒把權重從 SSD 載入記憶體；後續對話則用 cached 權重、快得多。Ollama 預設把載入的 model 留在記憶體 5 分鐘（`keep_alive` 預設值）、長時間不用會被 unload 釋放記憶體。

長時間穩定使用的場景可以延長 keep_alive：

```bash
OLLAMA_KEEP_ALIVE=-1 ollama serve     # 永久保留
OLLAMA_KEEP_ALIVE=2h ollama serve     # 保留 2 小時
```

`-1` 設定會持續佔用記憶體、適合「整天頻繁用」的工作流；偶爾用一次的場景保持預設、讓系統自動釋放更省記憶體。

### 對外暴露與信任邊界

預設 Ollama 只聽 [`127.0.0.1`](/llm/knowledge-cards/port-and-localhost/)、外部裝置連不上。讓 LAN 內其他機器（例如桌機跑 server、筆電當 client）能用、把 listen address 改成 `0.0.0.0`：

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

這個設定把 Ollama 暴露在整個區網、任何同網路裝置都能呼叫 API。信任邊界的三種典型情境：

- **家用 / 信任的辦公網路**：風險低、可以直接開
- **公共 Wi-Fi、共用網路**：透過 SSH tunnel 把 11434 隧道到遠端、或加防火牆規則限制 source IP
- **暴露到 Internet**：需要 reverse proxy 加 auth、Ollama 本身沒有內建身分認證

完整資料流判讀見 [0.7 隱私 / 資安資料流](/llm/00-foundations/privacy-data-flow/)。

### 版本管理

Ollama 釋出節奏快、每兩三週可能加新功能或修嚴重 bug。升級流程：

```bash
brew upgrade ollama
brew services restart ollama   # 若用 launchd service 跑
```

升級前先看 [release notes](https://github.com/ollama/ollama/releases)、確認三件事：

1. 是否引入 breaking API change（IDE plugin 可能要對應更新）
2. 是否棄用舊 model tag（拉新 tag 取代）
3. 是否帶來想要的新功能（例如新模型支援、加速優化）

## 排錯快速判讀

排錯段的設計是「先給操作原則、再列觸發條件」、讓讀者快速定位現象屬於哪一類。

### Port 11434 已被佔用

操作原則：先檢查是不是舊 Ollama 還在跑、再決定 kill 或換 port。[`lsof` / `pkill` 的角色](/llm/knowledge-cards/shell-background-process/)是找出佔用方並送終止訊號。

```bash
lsof -i :11434          # 看誰佔 11434
pkill -f "ollama serve" # 確認是舊 Ollama 才 kill
ollama serve &          # 重啟、& 是把 process 丟背景
```

需要兩個 Ollama 並存的場景、改 port 啟動：

```bash
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

IDE plugin 的 `apiBase` 也要對應改成 11435。

### 記憶體不足、模型崩潰

操作原則：先用 `ollama ps` 看實際載入了什麼、再對照 [0.5 記憶體預算](/llm/00-foundations/hardware-memory-budget/) 決定降級。

```bash
ollama ps
# NAME           ID      SIZE     PROCESSOR    UNTIL
# gemma4:31b...  abc123  18 GB    100% GPU     5 minutes from now
```

模型大小超過 Mac 記憶體預算時的可選路徑：

- 換較小 model（例如 31B → 14B）
- 換較激進量化（例如 Q5_K_M → Q4_K_M）
- 縮短 context window（在 IDE plugin 端設定）

### 模型載入很慢

操作原則：第一次載入慢屬於正常、後續呼叫如果還是慢、檢查 keep_alive 設定。

第一次載入 18 GB 權重需要 30 ~ 60 秒、屬於 SSD → RAM 的真實 I/O 時間。如果發現「每次第一個請求都慢」、表示 keep_alive 太短、模型每次被 unload 又重新載入。延長 keep_alive 解決：

```bash
OLLAMA_KEEP_ALIVE=1h ollama serve
```

代價是模型常駐記憶體、其他應用可用記憶體變少。

### Model cache 過大佔滿 SSD

操作原則：清理用 `ollama rm <tag>`、Ollama 才會同步更新 registry metadata。

```bash
ollama list             # 看哪些 model 佔空間
ollama rm <tag>         # 刪除單一 model
```

手動 `rm -rf ~/.ollama/models/` 會留下 registry metadata 不一致、後續 `ollama list` 出錯、`ollama pull` 也可能誤判已存在。需要完全重置的場景、用：

```bash
brew services stop ollama
rm -rf ~/.ollama
brew services start ollama
```

這會清掉所有 model 跟設定、重新從零開始。

## 跟其他伺服器並存

Ollama 設計上可以跟 LM Studio、llama.cpp 同時在一台 Mac 跑、預設 port 不同：

| 伺服器    | 預設 port | 適合主力場景               |
| --------- | --------- | -------------------------- |
| Ollama    | 11434     | 日常寫 code、CLI 工作流    |
| LM Studio | 1234      | GUI 探索新模型、視覺化參數 |
| llama.cpp | 8080      | 底層研究、自訂量化         |
| oMLX      | 8000      | 特化 MLX 場景              |

並存的好處是「主力穩定跑 Ollama、實驗模型用 LM Studio」、Continue.dev 等介面層可以同時設多個 model、UI 上下拉切換。並存設定範例見 [1.1 LM Studio](/llm/01-local-llm-services/lm-studio/#與-ollama-並存)。

## 小結

Ollama 是 2026 年 5 月本地 LLM 生態的預設選擇：學習曲線低、Gemma 4 MTP 一鍵支援、OpenAI 相容 API 出廠就有、生態最成熟。多數讀者只需要這一個伺服器、靠 model tag 切換不同 model 即可覆蓋日常工作。

下一章可選擇：

- 想對比 GUI 派的選擇：[1.1 LM Studio](/llm/01-local-llm-services/lm-studio/)
- 想了解底層 / Ollama 跟 llama.cpp 的關係：[1.2 llama.cpp](/llm/01-local-llm-services/llama-cpp/)
- 直接進入 VS Code 整合：[1.3 VS Code + Continue.dev](/llm/01-local-llm-services/vscode-continue-integration/)
