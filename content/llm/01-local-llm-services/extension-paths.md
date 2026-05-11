---
title: "1.6 延伸方向：Web UI、coding agent、產圖"
date: 2026-05-11
description: "日常路徑跑穩後可以玩的延伸：Open WebUI、aider、ComfyUI；先把基底跑穩再進階"
tags: ["llm", "extension", "open-webui", "aider", "diffusion"]
weight: 6
---

模組一前五章覆蓋了「Ollama + Continue.dev」這條最短路徑。日常路徑跑穩後，你可能會想往以下方向延伸：加裝 ChatGPT 風格的 Web UI、跑 coding agent、嘗試產圖。本章把這些延伸方向逐一列出、給優先順序、講清楚哪些是「換工具」、哪些是「換領域」。

關鍵原則：**先把寫 code 跑穩，再考慮延伸**。同時學三個延伸方向只會三邊都半生不熟。本章建議的順序是先 Web UI、再 coding agent、最後產圖；如果你只想嘗試一個，依自己最常用的場景挑。

## 本章目標

讀完本章後，你應該能：

1. 列出三條延伸方向的代表工具與基本定位。
2. 知道每個方向跟寫 code 主路徑的關係。
3. 判斷自己現階段該不該往延伸方向走。
4. 對「產圖」這條歧路建立正確認知（不是換 model 就好）。

## 延伸方向一：ChatGPT 風格 Web UI（Open WebUI）

**定位**：在瀏覽器跑一個類 ChatGPT 介面，連到本地 LLM 或雲端 LLM。屬於[三層架構](/llm/00-foundations/three-layer-architecture/)的介面層，跟 Continue.dev 同層、解決不同情境（瀏覽器 vs IDE）。

**典型使用情境**：

1. 不在寫 code 但想跟 LLM 對話（解釋技術概念、寫文章草稿）。
2. 跟同事 / 家人分享 LLM 使用，他們不會用 VS Code。
3. 從手機 / iPad 連回家裡 Mac 跑的 Ollama。
4. 多輪深度對話、希望有歷史紀錄保存。

### 主流選擇：Open WebUI

Open WebUI 是 open source 的 ChatGPT-clone，連 Ollama 與 OpenAI 相容 API。安裝最快路徑是 Docker：

```bash
docker run -d --name open-webui -p 3000:8080 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v open-webui:/app/backend/data \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

啟動後開 `http://localhost:3000`，註冊本地帳號（資料只存本機 SQLite），就有完整 ChatGPT 介面：

- 對話歷史保存（本地 SQLite）
- 多 model 切換、可同時對比兩個 model 回答
- 系統 prompt 自訂、prompt template 管理
- 上傳檔案分析（PDF、txt 等）
- 圖片支援（如果本地 model 是多模態）

**陷阱**：

1. 沒裝 Docker 的話要先學 Docker，是不小的前置學習。
2. Open WebUI 預設不需要驗證，跑在 `0.0.0.0` 會暴露在 LAN 上。要從外網用記得加 reverse proxy + auth。
3. 對話紀錄存在 Docker volume，刪 container 要小心保留 volume，否則歷史會消失。

**何時做這個延伸**：日常 Continue.dev + Ollama 跑穩、用了至少一週、確認本地 LLM 對你有用，再加 Open WebUI 擴展使用情境。

## 延伸方向二：Coding Agent（aider、Cline 等）

**定位**：比 Continue.dev 更主動的 LLM 寫 code 工具。Continue.dev 是「你提問、LLM 答」的對話模式；coding agent 是「你給目標、LLM 自己分多步驟改 code、跑測試、修錯誤」的代理模式。

**主流選擇**：

| 工具         | 介面         | 定位                                                          |
| ------------ | ------------ | ------------------------------------------------------------- |
| aider        | CLI          | git-aware，把 LLM 改的 diff 直接 commit，支援 multi-file edit |
| Cline        | VS Code 擴充 | 在 VS Code 內跑 agent，可以執行 shell command                 |
| Cursor Agent | Cursor 內建  | Cursor 訂閱戶可用，雲端綁定                                   |

**為什麼是 advanced**：coding agent 需要本地模型能「跟著規劃跑多步驟、用 tools、不偏離目標」。這部分是本地 LLM 的弱項（見 [1.5 期望管理](/llm/01-local-llm-services/expectation-management/)）；現階段本地模型跑 coding agent 的成功率明顯低於雲端旗艦。

**用 aider 跑本地 LLM 的最小範例**：

```bash
# 裝 aider
pip install aider-chat

# 在 git repo 內啟動，用本地 Ollama
aider --model ollama/gemma4:31b-coding-mtp-bf16 \
  --ollama-base-url http://localhost:11434
```

aider 會把當前 repo 的相關檔案打進 prompt、把 LLM 生成的 diff apply 到本機、自動 commit。簡單任務（單檔重構、加 test）成功率還行；複雜任務（跨檔案、需要規劃）失敗率高。

**陷阱**：

1. 本地 LLM 跑 aider 比跑 Continue.dev 慢得多，因為每輪 agent loop 都要重新處理長 context。
2. coding agent 對 long context 敏感，本地 [TTFT](/llm/00-foundations/why-llm-feels-slow/) 痛點被放大。
3. 失敗時 agent 可能 commit 不可用的 code，要記得 `git diff` 審過再 push。

**何時做這個延伸**：本地模型在 Continue.dev 對話模式下表現穩定，且你想看看「multi-step 自動化」能幫到什麼程度。對多數讀者，這條延伸在 2026 年 5 月時是「值得試一週，但不一定留下」。

## 延伸方向三：產圖（Stable Diffusion、Flux 等）

**定位**：跟 LLM 寫 code **完全不同的領域**。產圖用的是 **Diffusion 架構**，跟寫 code 用的 **Transformer 架構**是兩個獨立的神經網路類型。工具鏈、生態、硬體最適規格都不一樣。

這不是「換個 model 就好」，是「進另一個專業領域」。本章只給入口資訊，不展開教學。

**主流工具**：

| 工具          | 定位                                   | 適合誰                   |
| ------------- | -------------------------------------- | ------------------------ |
| Draw Things   | Mac 原生 app，GUI 友善，免費           | macOS 使用者入門首選     |
| ComfyUI       | 節點式工作流，跨平台，需要 Python 環境 | 想客製化流程、進階使用者 |
| AUTOMATIC1111 | Web UI，跨平台，需要 Python            | Linux / NVIDIA 玩家為主  |
| Diffusers     | Hugging Face 的 Python library         | 開發者、要嵌入產品       |

**主流模型**：

| 模型                 | 風格特色                       |
| -------------------- | ------------------------------ |
| Stable Diffusion 3.5 | 通用、社群成熟、生態最大       |
| Flux                 | 質感高、prompt 跟隨度高        |
| SDXL                 | SD 1.5 的進階版，仍有大量 LoRA |

**Apple Silicon Mac 跑產圖的現實**：

1. 24GB+ Mac 可以順暢跑 SDXL / Flux。記憶體需求其實比 LLM 低（一張圖 ~ 8GB），但對 GPU 算力敏感。
2. M4 Max 跑 Flux 生 1024x1024 圖約 15 ~ 30 秒一張，可接受。
3. Draw Things 在 Mac App Store 可下載，是最簡單的入門路徑。

**為什麼跟寫 code 適合分開學**：

1. **工具鏈各自獨立**：Ollama 服務 [Transformer](/llm/knowledge-cards/transformer/) LLM、Draw Things / ComfyUI 服務 [Diffusion](/llm/knowledge-cards/diffusion/) 模型、兩條路線的伺服器與生態互不通用。
2. **prompt 風格不同**：寫 code 是 instruction 形式、產圖是 descriptive prompt + negative prompt + sampler 參數。
3. **學習成本各自獨立**：產圖有自己的 LoRA、ControlNet、IP-Adapter、refiner 等概念體系、學起來等於進入新領域。
4. **硬體最適規格不同**：寫 code 看記憶體預算（[跑大模型](/llm/knowledge-cards/unified-memory/)）、產圖看 GPU 算力與 VRAM 頻寬。

**本指南的立場**：先把寫 code 跑穩、再考慮產圖。產圖屬於獨立的學習主題、另外找專門教材會學得更有效率。

## 給讀者的延伸順序

如果你想嘗試延伸方向，建議的順序：

1. **先用一個月本地 LLM 寫 code**。確認 Ollama + Continue.dev 對你有用、習慣了切換。
2. **第一個延伸：Open WebUI**。加裝最低成本（只多裝 Docker），擴展使用情境到非 VS Code 場景。
3. **第二個延伸：aider 或 Cline**。試 coding agent，評估本地模型能 handle 多複雜的多步驟任務。
4. **第三個延伸：產圖**。完全獨立的學習投入，跟前面工具鏈無關。

依序進階。先讓基底穩、再疊加延伸、學習曲線最平滑。

## 不在本章範圍內的延伸

下列延伸方向值得知道存在，但不在本指南內展開：

| 方向                                    | 為什麼不展開                                                          |
| --------------------------------------- | --------------------------------------------------------------------- |
| RAG（檢索增強生成）                     | 需要 vector database、文件 chunking、embedding 設計，是另一個完整主題 |
| Fine-tuning                             | 訓練流程跟跑現成模型是不同工程；資源、資料、評估都複雜                |
| Multi-modal（語音、影片）               | 工具鏈跟生態完全獨立                                                  |
| MCP（Model Context Protocol）伺服器整合 | 是工具串接協定，跟「在 Mac 跑 LLM」是不同方向                         |
| 部署到雲端 GPU / Linux server           | 本指南範圍只在 Apple Silicon Mac                                      |

需要這些方向時請另尋專門資源；硬塞進來會稀釋本指南「Mac 本地寫 code」這條最短路徑。

## 小結

延伸方向有三條：Web UI（Open WebUI、低成本、擴展使用情境）、coding agent（aider、進階、現階段本地能力受限）、產圖（完全獨立領域、不是換 model 就好）。先把寫 code 跑穩再做延伸；想做產圖就承認它是另一個學習主題、另開戰場。

讀到這裡，本指南的核心內容就完了。下一步是回到 [模組零](/llm/00-foundations/) 或 [模組一](/llm/01-local-llm-services/) 任一章節做深度閱讀，或實際打開終端機跑第一個 `ollama run`，把概念變成肌肉記憶。
