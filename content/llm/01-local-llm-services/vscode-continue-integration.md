---
title: "1.3 VS Code + Continue.dev 整合"
date: 2026-05-11
description: "安裝 Continue 擴充套件、config.json 設定、Cmd+L 對話 / Cmd+I 行內編輯快捷鍵"
tags: ["llm", "vscode", "continue-dev", "integration"]
weight: 3
---

把本地 LLM 接到 VS Code 是「本地 LLM 寫 code」工作流的真正起點。前面章節安裝的 Ollama 是[伺服器層](/llm/00-foundations/three-layer-architecture/)，本章要接的 Continue.dev 是**介面層**：使用者實際在編輯器裡按快捷鍵、打字、看 inline diff 的工具。

Continue.dev 是 2026 年 5 月時與本地 LLM 整合最成熟的 VS Code 擴充套件。對應到雲端世界、它的定位類似 Cursor、差別是 Continue.dev 預設綁本地、可以同時連雲端；Cursor 預設綁雲端、本地是次要 surface、設定深度較高。

本章假設你已經裝好 Ollama 並至少跑過一次 `ollama run`。沒裝過請先回 [1.0 Ollama](/llm/01-local-llm-services/ollama/)。

## 本章目標

讀完本章後，你應該能：

1. 安裝 Continue.dev 擴充套件。
2. 在 `~/.continue/config.json` 設定本地 Ollama 模型。
3. 用 Cmd+L 開對話、Cmd+I 做行內編輯。
4. 同時設定本地與雲端模型，按任務切換。
5. 排除 Continue 連不上 Ollama 的常見問題。

## 安裝擴充套件

Continue 擴充套件是 VS Code 內接到本地 LLM 的介面層入口、裝完才有 chat panel 與 inline edit 快捷鍵。在 VS Code 內按 Cmd+Shift+X 開啟 extensions panel、搜尋 `Continue`。第一個結果作者是 `Continue Dev, Inc.`（藍色 verified 標記）、點 Install。

裝完後左側 sidebar 多一個 Continue icon（一個小方塊）。第一次點開會跳出 onboarding、可以略過。

擴充套件本身是 open source、Continue Dev 帳號（公司提供的雲端服務 tier、跟 VS Code 的 Microsoft 帳號是兩件事）可選。「本地 LLM」場景使用 open source 部分就足夠、不必登入。

## 找到 config.json

Continue 的設定檔在 `~/.continue/config.json`（macOS 是 `/Users/<你的帳號>/.continue/config.json`）。第一次開 Continue 後檔案會自動產生。

開檔案：

```bash
code ~/.continue/config.json
```

或在 VS Code Continue panel 點右上角齒輪 icon，會直接開 config.json。

預設內容包含一些雲端範例 model（OpenAI、Anthropic、Mistral），我們要加自己的本地 model。

## 設定本地 Ollama 模型

把 `models` 陣列改成這樣：

```json
{
  "models": [
    {
      "title": "Local: Gemma 4 31B MTP",
      "provider": "ollama",
      "model": "gemma4:31b-coding-mtp-bf16",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Local autocomplete",
    "provider": "ollama",
    "model": "gemma4:e4b",
    "apiBase": "http://localhost:11434"
  },
  "embeddingsProvider": {
    "provider": "ollama",
    "model": "nomic-embed-text",
    "apiBase": "http://localhost:11434"
  }
}
```

每個欄位的意義：

| 欄位                   | 意義                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `models`               | 可在 chat panel 下拉選擇的對話模型清單                                                                                              |
| `tabAutocompleteModel` | 在編輯器裡邊打邊補完的模型（按 Tab 接受）、建議用小模型加快回應                                                                     |
| `embeddingsProvider`   | 把 codebase 索引成向量、用於語意搜尋的 [embedding 模型](/llm/knowledge-cards/embedding-model/)。要先 `ollama pull nomic-embed-text` |

Embedding model 的角色跟 chat / autocomplete model 不同：chat model 負責「跟你對話」、embedding model 負責「把文字壓成向量、用來做語意相似比對」、是 `@codebase` 功能的後端引擎。一般 chat model 沒法當 embedding model、要分開設定。

`provider: ollama` 是 Continue 內建的 Ollama 整合、比 `provider: openai` 多支援 model auto-pull 等功能。`apiBase` 不需要加 `/v1`、Continue 內部會處理。

存檔後 Continue 會自動 reload。

## 用 Cmd+L 開對話

Cmd+L 是把當前 buffer 餵進 chat 的快捷路徑、context 由選取範圍決定。回到 VS Code、按 `Cmd+L`（macOS）開啟 Continue chat panel。預設快捷鍵：

| 快捷鍵        | 動作                                              |
| ------------- | ------------------------------------------------- |
| `Cmd+L`       | 開啟 Continue panel、把當前選取的程式碼當 context |
| `Cmd+Shift+L` | 把當前選取加進現有對話 context                    |
| `Cmd+I`       | 在編輯器裡開 inline edit prompt                   |
| `Cmd+;`       | 接受 inline edit 結果                             |
| `Cmd+'`       | 拒絕 inline edit 結果                             |

按 `Cmd+L` 後 panel 開啟，下方輸入區可以打 prompt。如果先選了一段 code，那段 code 會自動加進 context，你可以直接問「解釋這段 code」「改成 async」「加 type annotation」。

第一次提問時 Ollama 會載入 model（30 ~ 60 秒）、看到 Continue panel 有 spinner 是預期的。之後同一個 model 會留在記憶體（[ollama keep_alive](/llm/01-local-llm-services/ollama/#模型常駐keep_alive)）、對話速度會快得多。

## 用 Cmd+I 做 inline edit

把游標放在你要修改的 code 上（或選取一段），按 `Cmd+I` 開 inline prompt。打字描述要做什麼，例如：

```text
加 type annotation
```

或：

```text
把這個 callback 改成 async/await
```

Enter 後 Continue 會把選取的 code + 你的指令送給本地模型，回傳的 diff 直接 inline 顯示。按 `Cmd+;` 接受、`Cmd+'` 拒絕。

陷阱是「選取範圍太大」。本地模型的 context window 雖然多半 8K 以上、但塞太多 code 會讓 [TTFT](/llm/knowledge-cards/ttft/) 暴增。把選取範圍縮在一個 function 或一個 block 內、體感最好。

## 同時設定本地與雲端模型（按任務切換）

寫 code 場景的常見配置是「本地當預設、雲端當大難題備援」。修改 `config.json`：

```json
{
  "models": [
    {
      "title": "Local: Gemma 4 31B MTP",
      "provider": "ollama",
      "model": "gemma4:31b-coding-mtp-bf16",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Cloud: Claude Sonnet 4.6",
      "provider": "anthropic",
      "model": "claude-sonnet-4-6",
      "apiKey": "sk-ant-xxx"
    },
    {
      "title": "Cloud: GPT-5",
      "provider": "openai",
      "model": "gpt-5",
      "apiKey": "sk-xxx"
    }
  ]
}
```

Continue chat panel 下方有 model selector，可以下拉切換。建議的切換時機：

| 任務類型                                  | 建議模型                                       |
| ----------------------------------------- | ---------------------------------------------- |
| 簡單 function 補完、加 type、寫 docstring | 本地 Gemma 4 31B                               |
| 解釋程式碼、寫單元測試                    | 本地 Gemma 4 31B                               |
| 跨檔案重構、規劃新模組                    | 雲端 Claude Sonnet / GPT-5                     |
| 深度 debug、解奇怪 bug                    | 雲端 Claude Sonnet / GPT-5                     |
| 處理含 NDA 的客戶 code                    | 本地（合規要求 prompt 留在本機時、走本地路線） |
| 寫 commit message                         | 本地（隱私 + 任務簡單）                        |

詳細的判斷邏輯見 [1.5 期望管理](/llm/01-local-llm-services/expectation-management/)。**安全 / 資料邊界面向**：同個 IDE 同時接本地跟雲端 provider、prompt routing 設錯就會把該走本地的 NDA / 客戶 code 送到雲端、見 [6.4 跨雲端 / 本地的資料邊界](/llm/06-security/cross-cloud-local-data-boundary/)；codebase / 外部文件 / 剪貼簿成為 prompt injection 攻擊面的判讀見 [6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/)。

## Codebase 索引與 @ 命令

`@` 命令是把外部 context（整個專案 / 終端機輸出 / docs）注入到 chat prompt 的擴充機制、讓 LLM 在回應時能參考超出選取範圍的資料。Continue 支援把整個 codebase 索引成向量資料庫、讓你用 `@codebase` 參考整個專案。要啟用：

1. `~/.continue/config.json` 設定 `embeddingsProvider`（前面已給範例）。
2. 開新 chat 後在 prompt 內打 `@codebase`，Continue 會自動把相關片段加進 context。
3. 第一次索引要 5 ~ 30 分鐘（看 repo 大小），之後增量更新。

`@codebase` 對中型專案（< 1000 檔案）效果不錯、本地模型有機會找到合適片段；對大型專案（10000+ 檔案）效果受限於 embedding model 品質。大型專案的退路：拆 workspace 縮小索引範圍、改用 `@file` 明確指定相關檔案、或換較強的 embedding model（例如雲端 OpenAI `text-embedding-3-large`）。

其他 `@` 命令：

| 命令        | 用途                                   |
| ----------- | -------------------------------------- |
| `@codebase` | 整個專案的語意搜尋                     |
| `@docs`     | 加進 documentation context（要先設定） |
| `@terminal` | 把終端機最後一段輸出加進 context       |
| `@file`     | 指定特定檔案                           |
| `@tree`     | 加進專案結構                           |
| `@open`     | 加進目前開啟的所有 tab                 |

## 處理 Continue 連不上 Ollama

常見錯誤訊息與處理：

| 錯誤訊息                                     | 處理                                                 |
| -------------------------------------------- | ---------------------------------------------------- |
| `Failed to fetch http://localhost:11434/...` | Ollama server 沒在跑。`brew services start ollama`   |
| `model 'xxx' not found`                      | 還沒 pull。`ollama pull xxx`                         |
| `address already in use`（Ollama 那邊）      | 已有 instance 在跑，`pkill -f "ollama serve"` 重啟   |
| Continue 無回應、長時間 spinner              | Model 正在載入。第一次 30 ~ 60 秒正常                |
| 對話內容亂碼 / 一直重複                      | 模型品質不夠或 temperature 太高，換較大模型或調 temp |
| Tab autocomplete 完全沒觸發                  | 確認 `tabAutocompleteModel` 設定、模型已 pull        |

排錯時先用 curl 驗證 Ollama 本身正常：

```bash
curl http://localhost:11434/api/tags
```

如果這個都回不出來、問題在 Ollama；如果這個正常但 Continue 連不上、問題在 Continue 設定。

排錯時的機制判讀：

- **`Failed to fetch`**：通常是 Ollama 沒跑、或 listen address 配置不一致（Continue config 跟 `OLLAMA_HOST` 對不上）。
- **`address already in use`**：另一個 Ollama instance 佔了 port、或 LM Studio 啟動時也搶 11434。先用 `lsof -i :11434` 找佔用方。
- **長時間 spinner**：第一次載入大模型（30 ~ 60 秒）正常；如果每次新 chat 都這樣、可能 keep_alive 太短、模型每次被 unload。
- **對話內容亂碼 / 一直重複**：小模型 capacity 不足以維持長 context 連貫性、或 `repeat_penalty` 預設值對該模型不合適。先換較大模型驗證是不是 model 本身的問題、再回頭調 temperature / repeat_penalty。
- **Tab autocomplete 沒觸發**：autocomplete 模型沒 pull 成功、或 model 名稱拼錯。`ollama list` 確認 model 真的在。

## 何時 Continue.dev 不適合

Continue.dev 是 VS Code 環境內最成熟的本地 LLM 介面層、但在以下情境會撞到設計邊界、需要找替代路徑：

| 情境                                              | 替代路徑                                                                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 非 VS Code-family 編輯器（Vim / Emacs / Sublime） | 各 editor 有自己的 LLM plugin（如 Vim 的 `llm.nvim`、Emacs 的 `gptel`）、Continue 本身僅支援 VS Code / JetBrains |
| Jupyter Notebook 環境                             | Notebook 的 cell 結構跟 .py 檔不同、Continue 對 .ipynb 支援有限、改用 Jupyter-AI 或自己用 LangChain              |
| 大型 monorepo（10000+ 檔案）                      | `@codebase` 索引效果受 embedding 品質限制、改拆 workspace 或用 `@file` 明確指定                                  |
| CLI-first / git-aware 工作流                      | [aider](/llm/01-local-llm-services/extension-paths/) 直接在 CLI 操作 git + LLM、適合「沒打開 IDE 也想用 LLM」    |
| 想跑 multi-step agent（自動探索 + 多輪修改）      | Cline、aider 等較完整 agent 工具的設計目標更貼近、Continue 偏單輪 chat + inline edit                             |

Continue 的甜蜜點是「VS Code 內、單檔到中型專案、人在駕駛位的 chat + inline edit」。離這個甜蜜點越遠、收益越低、改用 Cline / aider / Cursor 等工具更直接。

## Continue.dev 跟 Cursor 的取捨

如果你正考慮 Continue.dev vs Cursor，下表是寫 code 場景的取捨：

| 維度             | Continue.dev                                  | Cursor                                            |
| ---------------- | --------------------------------------------- | ------------------------------------------------- |
| 本地 LLM 支援    | First-class，多家 provider 完整支援           | 有，但設定較深、不是主要使用情境                  |
| 雲端 LLM 支援    | 多家 provider（OpenAI、Anthropic、本地）      | 主要綁 Cursor 自己的服務、能接 OpenAI / Anthropic |
| 訂閱費           | 免費（本地 LLM 完全免費；接雲端要自己付 API） | 月費 USD 20（含若干雲端用量）                     |
| Inline edit 體驗 | 良好（Cmd+I）                                 | 優秀（Cursor 的招牌）                             |
| Agent 模式       | 較陽春，主打 chat + edit                      | 較完整，有 multi-step agent                       |
| Codebase 索引    | 自家 embedding（本地或雲端）                  | 雲端索引（要 opt-out）                            |
| 隱私             | 完全可控（純本地）                            | 預設送 Cursor 雲端 telemetry                      |

對「本地 LLM 為主」的使用者，Continue.dev 是更直接的選擇。Cursor 是「雲端 LLM 為主、偶爾本地」的選擇。

## 小結

VS Code + Continue.dev 是 2026 年 5 月本地 LLM 寫 code 工作流的主流組合。設定不複雜：擴充套件裝完、`config.json` 設好 Ollama endpoint、Cmd+L 開對話、Cmd+I 行內編輯就能用。同時設本地與雲端模型可以按任務切換，是現階段的合理姿勢。

下一章：[1.4 寫 code 場景的模型選型優先順序](/llm/01-local-llm-services/model-selection-priority/)，回答「Ollama 跑起來該裝哪個 model」。
