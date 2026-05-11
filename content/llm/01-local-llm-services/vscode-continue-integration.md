---
title: "1.3 VS Code + Continue.dev 整合"
date: 2026-05-11
description: "安裝 Continue 擴充套件、config.json 設定、Cmd+L 對話 / Cmd+I 行內編輯快捷鍵"
tags: ["llm", "vscode", "continue-dev", "integration"]
weight: 3
---

把本地 LLM 接到 VS Code 是「本地 LLM 寫 code」工作流的真正起點。前面章節安裝的 Ollama 是[伺服器層](/llm/00-foundations/three-layer-architecture/)，本章要接的 Continue.dev 是**介面層**：使用者實際在編輯器裡按快捷鍵、打字、看 inline diff 的工具。

Continue.dev 是 2026 年 5 月時與本地 LLM 整合最成熟的 VS Code 擴充套件。對應到雲端世界，它的定位類似 Cursor，差別是 Continue.dev 預設綁本地、可以同時連雲端，而 Cursor 預設綁雲端、本地支援較陽春。

本章假設你已經裝好 Ollama 並至少跑過一次 `ollama run`。沒裝過請先回 [1.0 Ollama](/llm/01-local-llm-services/ollama/)。

## 本章目標

讀完本章後，你應該能：

1. 安裝 Continue.dev 擴充套件。
2. 在 `~/.continue/config.json` 設定本地 Ollama 模型。
3. 用 Cmd+L 開對話、Cmd+I 做行內編輯。
4. 同時設定本地與雲端模型，按任務切換。
5. 排除 Continue 連不上 Ollama 的常見問題。

## 安裝擴充套件

開 VS Code，按 Cmd+Shift+X 開啟 extensions panel，搜尋 `Continue`。第一個結果作者是 `Continue Dev, Inc.`（藍色 verified 標記），點 Install。

裝完後左側 sidebar 多一個 Continue icon（一個小方塊）。第一次點開會跳出 onboarding，可以略過。

擴充套件本身為 open source、登入帳號是可選的。Continue Dev 公司另有雲端服務 tier、「本地 LLM」場景使用 open source 部分就足夠。

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

`provider: ollama` 是 Continue 內建的 Ollama 整合，比 `provider: openai` 多支援 model auto-pull 等功能。`apiBase` 不需要加 `/v1`，Continue 內部會處理。

存檔後 Continue 會自動 reload。

## 用 Cmd+L 開對話

回到 VS Code，按 `Cmd+L`（macOS）開啟 Continue chat panel。預設快捷鍵：

| 快捷鍵        | 動作                                              |
| ------------- | ------------------------------------------------- |
| `Cmd+L`       | 開啟 Continue panel、把當前選取的程式碼當 context |
| `Cmd+Shift+L` | 把當前選取加進現有對話 context                    |
| `Cmd+I`       | 在編輯器裡開 inline edit prompt                   |
| `Cmd+;`       | 接受 inline edit 結果                             |
| `Cmd+'`       | 拒絕 inline edit 結果                             |

按 `Cmd+L` 後 panel 開啟，下方輸入區可以打 prompt。如果先選了一段 code，那段 code 會自動加進 context，你可以直接問「解釋這段 code」「改成 async」「加 type annotation」。

第一次提問時 Ollama 會載入 model（30 ~ 60 秒）、看到 Continue panel 有 spinner 是預期的。之後同一個 model 會留在記憶體（[ollama keep_alive](/llm/01-local-llm-services/ollama/)）、對話速度會快得多。

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

陷阱是「選取範圍太大」。本地模型的 context window 雖然多半 8K 以上，但塞太多 code 會讓 TTFT 暴增。把選取範圍縮在一個 function 或一個 block 內，體感最好。

## 同時設定本地與雲端模型

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

| 任務類型                                  | 建議模型                   |
| ----------------------------------------- | -------------------------- |
| 簡單 function 補完、加 type、寫 docstring | 本地 Gemma 4 31B           |
| 解釋程式碼、寫單元測試                    | 本地 Gemma 4 31B           |
| 跨檔案重構、規劃新模組                    | 雲端 Claude Sonnet / GPT-5 |
| 深度 debug、解奇怪 bug                    | 雲端 Claude Sonnet / GPT-5 |
| 處理含 NDA 的客戶 code                    | 一定用本地                 |
| 寫 commit message                         | 本地（隱私 + 任務簡單）    |

詳細的判斷邏輯見 [1.5 期望管理](/llm/01-local-llm-services/expectation-management/)。

## Codebase 索引與 @ 命令

Continue 支援把整個 codebase 索引成向量資料庫，讓你用 `@codebase` 參考整個專案。要啟用：

1. `~/.continue/config.json` 設定 `embeddingsProvider`（前面已給範例）。
2. 開新 chat 後在 prompt 內打 `@codebase`，Continue 會自動把相關片段加進 context。
3. 第一次索引要 5 ~ 30 分鐘（看 repo 大小），之後增量更新。

`@codebase` 對中型專案（< 1000 檔案）效果不錯，本地模型有機會找到合適片段；對大型專案（10000+ 檔案）效果受限於 embedding model 品質。

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

如果這個都回不出來，問題在 Ollama；如果這個正常但 Continue 連不上，問題在 Continue 設定。

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
