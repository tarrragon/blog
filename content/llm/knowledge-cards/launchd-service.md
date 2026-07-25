---
title: "launchd Service"
date: 2026-05-12
description: "macOS 原生的服務管理機制、把 process 註冊成自動啟動的 daemon 或 agent"
weight: 1
tags: ["llm", "knowledge-cards", "macos"]
---

launchd Service 的核心概念是「macOS 用來管理常駐 process 生命週期的原生機制」。launchd 本身是 macOS 啟動後的第一個 process（PID 1）、由它負責拉起其他系統服務跟使用者註冊的背景任務。本地 LLM 場景中、Ollama 等[推論伺服器](/llm/knowledge-cards/inference-server/)透過 launchd 設定成「開機自動啟動、登入時自動拉起」、就不需要每次重開機都手動跑 `ollama serve`。

## 概念位置

launchd service 用一份 plist（property list、XML 格式設定檔）描述「要跑哪個程式、何時啟動、出問題時要不要重啟、log 寫到哪裡」。plist 放在三個位置之一、決定服務的觸發範圍：

| 路徑                      | 角色                 | 何時觸發               |
| ------------------------- | -------------------- | ---------------------- |
| `~/Library/LaunchAgents/` | 使用者 agent         | 該使用者登入時         |
| `/Library/LaunchAgents/`  | 全機所有使用者 agent | 任何使用者登入時       |
| `/Library/LaunchDaemons/` | 系統 daemon、需 root | macOS 開機時、不需登入 |

[Homebrew](/llm/knowledge-cards/homebrew/) 的 `brew services` 子命令是 launchd 的 wrapper、產生 plist 並放進 `~/Library/LaunchAgents/`、避免使用者直接手寫 XML。Apple Silicon Mac 上產生的檔名形式是 `homebrew.mxcl.<service>.plist`。

## 可觀察訊號與例子

執行 `brew services start ollama` 後可以驗證實際發生的事：

```bash
# 看 plist 內容
cat ~/Library/LaunchAgents/homebrew.mxcl.ollama.plist

# 用 launchctl 看服務狀態
launchctl list | grep ollama

# 看服務 log（Apple Silicon）
tail -f /opt/homebrew/var/log/ollama.log
```

plist 內常見的鍵：`ProgramArguments`（要跑哪個指令）、`RunAtLoad`（開機就啟動）、`KeepAlive`（crash 後自動拉回）、`StandardOutPath` / `StandardErrorPath`（log 路徑）。出問題時先看 log 路徑指向的檔案、能直接看到 service 的 stdout / stderr。

服務管理常用指令：

```bash
brew services list             # 列出所有由 brew 管理的服務
brew services start ollama     # 啟動 + 註冊自動啟動
brew services stop ollama      # 停掉服務、保留 plist
brew services restart ollama   # 升級套件後重啟
```

直接用系統的 `launchctl` 也行、但語意較底層、實務上有 brew 包裝就用 brew。

## 設計責任

選擇「launchd service」vs「前景手動跑 `ollama serve`」的判讀：日常用機建議用 launchd service、好處是重開機自動拉起、出問題的 log 有固定位置可看；只在偶爾用本地 LLM 的場景、保持手動跑反而省記憶體（沒在用就停掉）。升級套件後記得 `brew services restart`、否則跑的還是舊版二進位。
