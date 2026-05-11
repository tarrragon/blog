---
title: "模組一：本地 LLM 服務的安裝與應用"
date: 2026-05-11
description: "Ollama、LM Studio、llama.cpp 的安裝與差異、VS Code + Continue.dev 整合、模型選型與期望管理"
tags: ["llm", "local-llm-services", "ollama", "lm-studio", "continue-dev"]
weight: 1
---

本模組的核心目標是把 [模組零](/llm/00-foundations/) 的心智模型落地到實際安裝步驟與工作流。網路上多數本地 LLM 教學是「列三個工具裝法」，缺乏選型脈絡與期望管理；本模組會先回答「為什麼選這個」，再給「怎麼裝」與「裝完之後該調哪些設定」。

讀完本模組後，你應該能在自己的 Mac 上裝好一個本地 LLM 工作流，並知道它的能力邊界、什麼時候該切回雲端。

## 章節列表

| 章節                                                           | 主題                                 | 關鍵收穫                                                                  |
| -------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------- |
| [1.0](/llm/01-local-llm-services/ollama/)                      | Ollama：主流推論伺服器               | 一行 brew 裝完、`ollama run` 一鍵跑 Gemma 4 MTP、OpenAI 相容 API on 11434 |
| [1.1](/llm/01-local-llm-services/lm-studio/)                   | LM Studio：GUI 探索模型              | 內建模型瀏覽器、speculative decoding 設定面板、適合探索新模型             |
| [1.2](/llm/01-local-llm-services/llama-cpp/)                   | llama.cpp：底層引擎                  | 直接面對 GGUF 與量化選項、MTP 仍 beta、需要進階設定                       |
| [1.3](/llm/01-local-llm-services/vscode-continue-integration/) | VS Code + Continue.dev 整合          | 安裝擴充套件、config.json 設定、Cmd+L / Cmd+I 快捷鍵                      |
| [1.4](/llm/01-local-llm-services/model-selection-priority/)    | 寫 code 場景的模型選型優先順序       | Gemma 4 31B MTP → Qwen3-Coder 30B → Qwen3 14B → gpt-oss 20B 的取捨理由    |
| [1.5](/llm/01-local-llm-services/expectation-management/)      | 期望管理：本地 LLM 的擅長領域與分工  | 本地是免費的初階 pair programmer，不是 Claude 替代品；混用是現階段正解    |
| [1.6](/llm/01-local-llm-services/extension-paths/)             | 延伸方向：Web UI、coding agent、產圖 | 先把寫 code 跑穩，再評估 Open WebUI、aider 等延伸；產圖另闢戰場           |

## 推論伺服器選型總表

模組零已建立的三層架構視角告訴你 Ollama、LM Studio、llama.cpp 都屬於**伺服器層**。本模組要回答的是這三者的具體差異：

| 維度                  | Ollama                                | LM Studio                      | llama.cpp                               |
| --------------------- | ------------------------------------- | ------------------------------ | --------------------------------------- |
| 介面                  | CLI + REST API                        | GUI + REST API                 | CLI only（server 子命令需自編譯）       |
| 學習曲線              | 低（一行裝完）                        | 低（一鍵安裝）                 | 中高（編譯、量化、參數要自己選）        |
| 模型瀏覽器            | 命令列 `ollama list`，registry 在網頁 | GUI 內建，直接搜尋下載         | 沒有，要自己去 Hugging Face 下載        |
| Gemma 4 MTP（2026/5） | v0.23.1 內建                          | 支援，要在 UI 開啟 speculative | 仍 beta，drafter 整合是 feature request |
| 適合誰                | 多數工程師、想快速開始                | GUI 派、探索模型階段           | 進階使用者、研究、特殊量化              |
| 同台共存              | 可以，預設 port 11434                 | 可以，預設 port 1234           | 可以，預設 port 8080                    |

讀完本表後的決策建議是：**先裝 Ollama，跑穩後再評估其他**。LM Studio 可以同時裝來探索模型，但日常主力建議 Ollama；llama.cpp 暫時不需要直接接觸（Ollama 內部已經用 llama.cpp）。

## 為什麼這個順序

本模組章節順序的設計脈絡：

1. **先 1.0 Ollama**：學習曲線最低、生態最成熟、Gemma 4 MTP 一鍵支援。多數讀者裝完這個就能開始用。
2. **再 1.1 LM Studio**：給「想要可視化探索」的讀者另一條路；也可以跟 Ollama 並存。
3. **接 1.2 llama.cpp**：澄清網路上「llama.cpp 才是真本地」的迷思，給進階讀者完整背景。
4. **再 1.3 VS Code + Continue.dev**：把伺服器接到日常工作環境，這才是寫 code 的真正起點。
5. **然後 1.4 模型選型**：伺服器跑起來後該裝哪個模型，給優先順序。
6. **再 1.5 期望管理**：用一週後該怎麼判斷「值不值得繼續用」「什麼時候切雲端」。
7. **最後 1.6 延伸方向**：日常路徑穩了再玩 Web UI、coding agent、產圖。

每一章可以單獨讀，但若你是第一次接觸本地 LLM，照順序讀最不容易迷路。

## 一個小時的最短路徑

如果你沒時間讀完整本模組、只想用一小時搞定本地 LLM 寫 code 的最基本工作流，下面是最短路徑：

```bash
# 1. 裝 Ollama（5 分鐘）
brew install ollama
ollama serve &

# 2. 拉模型（首次下載約 20 ~ 30 分鐘，看網速）
ollama run gemma4:31b-coding-mtp-bf16

# 3. 在 VS Code 裝 Continue 擴充套件（2 分鐘）
# 4. 設定 ~/.continue/config.json（5 分鐘）
# 5. 試用 Cmd+L（對話）、Cmd+I（行內編輯）（剩下時間）
```

需要 32GB+ Mac 才能流暢跑這個 model；16GB / 24GB 請改用 [1.4 模型選型](/llm/01-local-llm-services/model-selection-priority/) 的對照表選對應大小的模型。完整步驟在 [1.0 Ollama](/llm/01-local-llm-services/ollama/) 跟 [1.3 VS Code + Continue.dev](/llm/01-local-llm-services/vscode-continue-integration/)。

## 跑穩之後該做什麼

裝完不是終點。本地 LLM 跟雲端的差別在於「需要持續調教」。跑穩後建議的後續工作：

1. **用一週實測**：把日常工作流真實餵進去、記錄通過率與痛點、用真實任務當判讀依據而非示範任務。
2. **建立切換習慣**：明確哪些任務交給本地、哪些切雲端。詳見 [1.5 期望管理](/llm/01-local-llm-services/expectation-management/)。
3. **觀察記憶體與發熱**：開 Activity Monitor 看記憶體 swap 狀態、機殼溫度是否過高。
4. **追新模型**：本地模型發布速度很快、每 2 ~ 3 個月會有新候選、值得追蹤。
5. **判斷是否升級硬體**：用一個月後若限制都來自記憶體、再評估升級 Mac；先確認痛點再投資硬體。

## 不在本模組內的主題

本模組不討論：

1. 訓練、fine-tuning、LoRA 微調 — 跟「跑現成模型」是不同的工程問題。
2. 部署到雲端 GPU、Linux server — 本指南範圍只在 Apple Silicon Mac。
3. Cursor、Windsurf、Cline 等其他 IDE 整合 — Continue.dev 是與本地 LLM 整合最成熟的選擇，其他工具的整合度視版本而定。
4. 詳細的 benchmark 跑分方法 — 本指南只引用官方數據，自己跑分屬於另一個工程主題。

需要這些主題時請另尋專門資源；硬塞進來只會讓「Mac 本地寫 code」這條最短路徑被淹沒。
