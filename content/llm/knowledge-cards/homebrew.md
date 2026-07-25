---
title: "Homebrew"
date: 2026-05-12
description: "macOS 上社群維護的套件管理器、用一行指令安裝 CLI 工具與背景服務"
weight: 1
tags: ["llm", "knowledge-cards", "macos"]
---

Homebrew 的核心概念是「macOS 的社群套件管理器、用 `brew install` 一行裝完 CLI 工具或 GUI 程式」。對本地 LLM 場景的角色是「[Ollama](/llm/knowledge-cards/inference-server/)、llama.cpp 等命令列工具的標準安裝入口」、把編譯、依賴管理、PATH 設定、二進位放置位置都自動化。

## 概念位置

Homebrew 在 macOS 跟使用者要安裝的工具之間、扮演「公開 registry + 本地套件管理」的角色。它維護一份名為「formula」的 Ruby 腳本清單、每個 formula 描述某個工具怎麼下載、編譯、安裝。執行 `brew install ollama` 時、Homebrew 找到 ollama formula、下載對應 bottle（預編譯二進位）、放到 `/opt/homebrew/`（Apple Silicon）或 `/usr/local/`（Intel Mac）、再把可執行檔 symlink 到 `/opt/homebrew/bin/`。新機從零的完整安裝順序（含第一次裝 Homebrew、PATH 設定與晶片前綴差異）見 [macOS 新機基礎建設](/macos/macos_new_machine_setup/)。

`brew services` 是 Homebrew 附帶的服務管理子命令、把指令封裝成 macOS 原生的 [launchd service](/llm/knowledge-cards/launchd-service/)、處理「開機自動啟動 / 停止 / 重啟」需求。

## 可觀察訊號與例子

日常會碰到的 brew 指令：

| 指令                  | 用途                                   |
| --------------------- | -------------------------------------- |
| `brew install <pkg>`  | 安裝套件                               |
| `brew upgrade <pkg>`  | 升級單一套件                           |
| `brew services start` | 把套件註冊成 launchd service、立刻啟動 |
| `brew services list`  | 列出目前由 brew 管理的常駐服務         |
| `which <bin>`         | 確認可執行檔在 PATH 上的實際路徑       |
| `brew --prefix`       | 查 Homebrew 的安裝根目錄               |

Apple Silicon Mac 上的關鍵路徑是 `/opt/homebrew/`、子資料夾各有角色：`bin/`（可執行檔）、`var/log/`（服務 log）、`Cellar/`（套件實際內容）、`opt/`（版本無關的 symlink）。看到「`/opt/homebrew/var/log/ollama.log`」時、就是 brew 管理的 Ollama 服務 log 位置。

## 設計責任

用 brew 安裝 vs 用官方 .dmg / .pkg 的取捨：CLI 工具（ollama、llama.cpp、git 等）走 brew、好處是統一升級路徑；GUI 應用（LM Studio、Docker Desktop 等）多半改下載官方安裝包、因為 brew cask 不一定即時跟上版本。第一次裝 Homebrew 自己用官方 install script（在 [brew.sh](https://brew.sh)）、之後其他工具都從 brew 走。
