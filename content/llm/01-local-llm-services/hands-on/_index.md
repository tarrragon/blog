---
title: "Hands-on：本地 AI 工具實作筆記"
date: 2026-05-11
description: "Ollama / ComfyUI / Whisper / Piper TTS：實際安裝、驗證、跑通的紀錄。隨工具版本演化、跟 1.x 原理章節互補。"
tags: ["llm", "hands-on", "ollama", "comfyui", "whisper", "tts"]
weight: 99
---

本子資料夾收錄本地 AI 工具的實際安裝跟驗證紀錄。跟 1.x 原理章節的關係：

| 1.x 原理章節              | Hands-on 紀錄                               |
| ------------------------- | ------------------------------------------- |
| 為什麼選 Ollama           | 實際 `brew install` + `ollama pull` 流程    |
| Speculative decoding 原理 | MTP 模型實際載入 + 速度量測                 |
| ComfyUI 在生態的位置      | 實際 git clone + Python 環境 + 模型路徑配置 |

本資料夾的內容**會隨工具版本演化**：指令、目錄結構、相依套件版本都會變。寫的時間戳記在每篇開頭、版本資訊在 frontmatter。跟 1.x 原理章節的差別是「原理跨工具世代不變、實作筆記是當下這版的快照」。

## 章節列表

| 章節                                                                                                          | 主題                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| [Quickstart：clone repo 後跑通所有 demo](/llm/01-local-llm-services/hands-on/quickstart/)                     | 4 步驟整合 setup、跑 RAG / MCP / permission demo、跨 hands-on 系列導讀                                                               |
| [Ollama 安裝 + Gemma 模型](/llm/01-local-llm-services/hands-on/ollama-setup/)                                 | brew install、ollama pull、curl 驗證                                                                                                 |
| [ComfyUI + Stable Diffusion XL](/llm/01-local-llm-services/hands-on/comfyui-setup/)                           | git clone、Python 環境、SDXL 模型放哪                                                                                                |
| [Whisper 語音轉文字](/llm/01-local-llm-services/hands-on/whisper-setup/)                                      | `brew install whisper-cpp` + Metal 加速、GGML 模型選擇、`whisper-cli` + ffmpeg 驗證轉錄                                              |
| [Piper TTS 文字轉語音](/llm/01-local-llm-services/hands-on/piper-tts-setup/)                                  | 下載 binary、voice 選擇、wav 輸出                                                                                                    |
| [RAG demo：用 blog content 當 corpus](/llm/01-local-llm-services/hands-on/rag-demo/)                          | embedding + retrieval、串 Ollama                                                                                                     |
| [MCP server demo：暴露 blog content](/llm/01-local-llm-services/hands-on/mcp-demo/)                           | 最小 MCP server、給 LLM 用                                                                                                           |
| [權限邊界實驗：LLM 改檔案 / 寫 shell 誰執行](/llm/01-local-llm-services/hands-on/permission-boundary/)        | LLM 是 pure function、wrapper 才是權限 gate、`--dry-run` / `--confirm` / `--auto` 取捨                                               |
| [跨資料夾風格 follow 任務的 model size 對比](/llm/01-local-llm-services/hands-on/instruction-following-test/) | 1B vs 4B 在「讀資料夾、follow 既有格式、寫新章節」任務上的 structural metrics phase transition                                       |
| [LLM 運行中 + 結束的資源管理](/llm/01-local-llm-services/hands-on/resource-management/)                       | RAM / 磁碟 / port 三 dimension 觀察、Ollama auto-unload vs ComfyUI persistent lifecycle、實測釋放數字、自動化 cleanup shell function |
| [RAG / MCP 的資源 footprint](/llm/01-local-llm-services/hands-on/rag-mcp-resources/)                          | RAG ingest / query / MCP server 三階段 RAM / 磁碟 / process 實測、多模型並存 RAM 衝突、長期累積管理                                  |

## 通用前置

所有工具都假設你的 Mac 滿足：

- Apple Silicon Mac（M1 / M2 / M3 / M4）
- macOS 14 (Sonoma) 或以上
- Homebrew 安裝完成（`brew --version` 可看版本）
- 至少 16 GB 統一記憶體（24 GB+ 較順）
- 至少 20 GB 可用磁碟空間（本系列總共會佔約 15 GB）

需要 Python 環境的工具（ComfyUI、Whisper）會用 venv 隔離、不污染系統 Python。

## 驗證紀錄環境

本系列的指令在以下環境驗證：

| 項目     | 版本                             |
| -------- | -------------------------------- |
| macOS    | Darwin 24.3.0（Sonoma 14.x）     |
| Homebrew | 由 `/opt/homebrew/bin/brew` 提供 |
| Python   | 3.x（系統或 pyenv 都可）         |
| 驗證日期 | 2026-05-11                       |

換 Mac 規格、換 macOS 版本、半年後再讀本系列、指令可能要小調整、但**前置設定的種類跟驗證步驟的結構**通常不變。看到指令跑不過時、回 1.7 [排錯方法論](/llm/01-local-llm-services/troubleshooting/) 的三層架構定位、不要把錯誤訊息當絕對。
