---
title: "1.2 llama.cpp：底層推論引擎"
date: 2026-05-11
description: "GGUF 格式、量化、MTP 仍 beta；多數讀者不需要直接接觸，Ollama 已經包好"
tags: ["llm", "llama-cpp", "server"]
weight: 2
---

llama.cpp 是本地 LLM 生態的**底層推論引擎**，2023 年由 ggerganov 釋出，後來成為 Ollama、LM Studio 等高層工具的內部 backend。它的核心承諾是「用純 C++ 寫一個高效能的 GGUF 模型推論器，跨平台、CPU/GPU/Apple Metal 都能跑」。

對寫 code 場景的多數讀者來說，**llama.cpp 是「不需要直接接觸」的層**。Ollama 已經把它包好，使用者看到的是 model tag 跟 CLI；llama.cpp 自己的編譯、量化、參數設定都被抽象掉。本章的目的是澄清網路上「llama.cpp 才是真本地、Ollama 是壓榨版」這類迷思，並給少數真的需要直接用 llama.cpp 的場景一條路。

## 本章目標

讀完本章後，你應該能：

1. 理解 llama.cpp 在三層架構中的位置。
2. 知道 Ollama 與 llama.cpp 的關係（包含 / 上游）。
3. 判斷自己什麼情境下需要直接用 llama.cpp、什麼情境不用。
4. 看懂 GGUF 格式與量化標籤（Q4_K_M、Q5_K_S 等）。
5. 對「llama.cpp 整合 Gemma 4 MTP」這類消息建立判讀反射。

## llama.cpp 在哪一層

llama.cpp 同時跨[三層架構](/llm/00-foundations/three-layer-architecture/)的兩層：

1. **推論引擎**（library）：核心 C++ library，把 GGUF 權重載入、跑 forward pass。Ollama、LM Studio、許多其他工具的 backend 就是這個 library。
2. **CLI 工具與 server**（`llama-cli`、`llama-server`）：附帶的命令列工具與 HTTP server，可以直接拿來用，但需要自己編譯與配置。

當你看到「我用 Ollama 跑 Gemma 4」，實際發生的事是：

```text
你的指令
  ↓
Ollama CLI / server（包裝層、模型管理）
  ↓
llama.cpp library（推論核心）
  ↓
Metal API（Apple Silicon GPU）
  ↓
Apple Silicon 硬體
```

所以「Ollama vs llama.cpp」不是兩個競爭品，是「上層包裝」跟「底層引擎」的關係。

## Ollama 跟 llama.cpp 的關係

Ollama 是 llama.cpp 的下游 wrapper，但**不是 fork-and-track 那種同步**。Ollama 維護自己的 vendored llama.cpp copy，加上他們自己的 patches；新功能進入 Ollama 的順序通常是：

1. llama.cpp 上游加新功能或修 bug
2. Ollama 把該 commit cherry-pick 進來
3. Ollama 發新版

但反過來也成立：**Ollama 有時搶先在 fork 裡加上游還沒接受的功能**，例如 Gemma 4 MTP 在 2026/5/7 的 Ollama v0.23.1 一鍵支援，當時 llama.cpp 上游的 Gemma 4 MTP 整合還是 feature request。

這個關係的啟示：

1. **不能假設「llama.cpp 比 Ollama 先進」**。實際情況視功能而定。
2. **看版本要看具體 release notes**，不是看主版本號。
3. **直接用 llama.cpp 不一定更接近上游**。Ollama 的 patches 有時是「上游應該要有但還沒接受」的功能。

## 什麼情境真的需要直接用 llama.cpp

絕大多數寫 code 場景，Ollama 完全夠用。直接用 llama.cpp 的合理情境只有少數：

| 情境                                             | 為什麼 Ollama 不夠                                  |
| ------------------------------------------------ | --------------------------------------------------- |
| 想自己量化模型（從 Safetensors 轉 GGUF）         | Ollama 不提供量化工具，要用 llama.cpp 的 `quantize` |
| 想跑 Ollama registry 沒收的特殊模型              | 要自己下載 GGUF、自己編譯 server                    |
| 想用 llama.cpp 最新 commit 的新功能              | Ollama 還沒 cherry-pick                             |
| 嵌入式 / 受限環境，要把 llama.cpp 編譯進別的 app | Ollama 是獨立 daemon，不能 embed                    |
| 純研究、想看推論程式碼                           | llama.cpp 是 open source、可讀                      |

寫 code 場景的讀者通常不命中以上任何一條。

## 安裝（如果你真要試）

從原始碼編譯：

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make
```

或用 Homebrew（社群維護，版本可能稍舊）：

```bash
brew install llama.cpp
```

裝完後常用命令：

```bash
# CLI 對話
llama-cli -m /path/to/model.gguf -p "Hello"

# HTTP server
llama-server -m /path/to/model.gguf --port 8080 --host 127.0.0.1
```

`llama-server` 啟動後在 `localhost:8080` 提供 OpenAI 相容 API：

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "any-name",
    "messages": [{"role": "user", "content": "Hi"}],
    "stream": false
  }'
```

`model` 欄位 llama-server 忽略，因為它一次只 serve 一個模型（不像 Ollama 可以動態切換）。

## GGUF 格式與量化標籤

GGUF（GGML Unified Format）是 llama.cpp 定義的模型權重格式，把模型權重、tokenizer、metadata 打包成單一檔案。Ollama 內部存的就是 GGUF。

常見量化標籤：

| 標籤       | bits/權重 | 品質         | 用途                 |
| ---------- | --------- | ------------ | -------------------- |
| F32        | 32        | 原始         | 訓練、研究、極端品質 |
| F16 / BF16 | 16        | 幾乎無損     | 評估、有大量記憶體   |
| Q8_0       | 8         | 幾乎無損     | 32GB+ Mac、品質敏感  |
| Q6_K       | 6.56      | 接近無損     | 平衡                 |
| Q5_K_M     | 5.5       | 輕微衰減     | 24GB Mac 甜蜜點      |
| Q4_K_M     | 4.5       | 可察覺但實用 | 最主流               |
| Q4_K_S     | 4.25      | 略遜 Q4_K_M  | 記憶體吃緊時退一步   |
| Q3_K_M     | 3.5       | 明顯衰減     | 不建議 coding 任務   |
| Q2_K       | 2.5       | 嚴重衰減     | 實驗用               |

`_K_M`、`_K_S` 的 K 指 K-quants（更先進的量化方法），M / S 指 mixed-medium / mixed-small（不同層用不同量化）。實務上選 `Q4_K_M` 或 `Q5_K_M` 是寫 code 場景的甜蜜點；極端記憶體緊張才往 `Q3` 走，但通常會發現換較小模型的 `Q5` 比強塞大模型的 `Q3` 好。

## Gemma 4 MTP 在 llama.cpp 的狀態（2026/5）

2026 年 5 月時：

- **speculative decoding 框架**：llama.cpp 已有 `--draft-model` 參數，整體 speculative decoding 功能 beta 階段。
- **Gemma 4 官方 drafter 整合**：feature request 開著（GitHub issue 上有討論），但尚未合進主分支。
- **Ollama 對應狀態**：v0.23.1 已一鍵支援 `gemma4:31b-coding-mtp-bf16`。

這是少見的「Ollama 領先 llama.cpp 上游」情境，原因是 Ollama 團隊接到 Google 的合作後直接做 patch、不等上游 review 流程。

實務啟示：

1. 想用 Gemma 4 MTP，**直接用 Ollama 是最快路徑**。
2. 想在 llama.cpp 直接跑 Gemma 4 MTP，要自己編譯帶上 Ollama 的 patches，或等上游合進來。
3. 看到「llama.cpp 已整合 Gemma 4 MTP」的網路文章，先去 [llama.cpp 的 PR 列表](https://github.com/ggerganov/llama.cpp/pulls) 確認時間點。

## llama.cpp 對 Apple Silicon 的優化

llama.cpp 對 Apple Silicon 有針對性優化：

1. **Metal backend**：在 macOS 上自動啟用 Metal，把 GPU 算力吃滿。
2. **NEON / AMX**：CPU 上用 ARM 向量指令集加速 dequantization。
3. **Unified Memory aware**：不像 NVIDIA GPU 要把資料搬進 VRAM，Apple Silicon 直接共用記憶體，省 PCIe 傳輸。

這些優化都「免費」，不用使用者特別設定。但跟 [MLX](/llm/00-foundations/mlx-mtp-omlx/) 比，llama.cpp 用的是 Metal 而不是 MLX framework；兩者效能各有勝負，差距通常 10 ~ 30%，不是「天差地遠」。

陷阱是看到「MLX 比 llama.cpp 快 N 倍」這類說法時，要追問：

1. 哪個模型？
2. 哪個量化？
3. 哪台 Mac？
4. llama.cpp 哪個版本？
5. 量測腳本是什麼？

多數網路 benchmark 沒有完整變數控制，差距常被誇大。對寫 code 場景的使用者，這個差距不值得糾結。

## 直接用 llama.cpp 跟 Ollama 並存

如果你真的想試 llama.cpp，可以跟 Ollama 並存（port 不同）：

| 伺服器       | 預設 port |
| ------------ | --------- |
| Ollama       | 11434     |
| llama-server | 8080      |
| LM Studio    | 1234      |

Continue.dev 可以同時連兩個：

```json
{
  "models": [
    {
      "title": "Ollama default",
      "provider": "ollama",
      "model": "gemma4:31b-coding-mtp-bf16",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "llama.cpp experimental",
      "provider": "openai",
      "model": "any",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

## 給多數讀者的建議

直接用 llama.cpp 的學習成本比 Ollama 高，但**換來的好處對寫 code 場景的使用者通常不重要**。如果你不是「自己量化模型」「跑特殊冷門模型」「需要 llama.cpp 最新 commit」這三種情境，**就用 Ollama**。

把 llama.cpp 當成「Ollama 背後的引擎、值得知道存在、但不需要直接面對」。這個定位足夠應付網路上 95% 的相關討論。

## 小結

llama.cpp 是 Ollama 與 LM Studio 的底層推論引擎，定位是 library 而不是面向終端使用者的工具。多數寫 code 場景的讀者不需要直接接觸；Ollama 已經把 GGUF、量化、Metal backend、speculative decoding 都包好。看到「llama.cpp 整合 X」的消息時，回到本章追問版本與時間點，避開過時或錯誤資訊。

下一章：[1.3 VS Code + Continue.dev 整合](/llm/01-local-llm-services/vscode-continue-integration/)，把伺服器接到日常編輯器，這才是寫 code 的真正起點。
