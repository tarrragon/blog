---
title: "環境可重現性與配置分類"
date: 2026-06-29
description: "想釐清哪些配置該進 dotfile repo、哪些不該進時回來讀"
weight: 1
tags: ["dotfile", "workflow"]
---

Dotfile 管理的核心能力是**環境可重現性**：把個人開發環境的配置狀態變成版控下的代碼，讓任何一台空白機器都能用一份 Git repo 還原成你熟悉的工作桌面。

## 什麼是 Dotfile

Unix 系統用檔名開頭的 `.` 標記隱藏檔。shell 配置（`.bashrc`、`.zshrc`）、Git 設定（`.gitconfig`）、SSH 設定（`.ssh/config`）、以及 `~/.config/` 底下各種工具的配置目錄，都屬於這個範疇。這些檔案決定了你的工作環境怎麼運作：shell 的 prompt 長什麼樣、alias 有哪些、editor 用什麼 keymap、terminal 的配色方案、視窗管理器怎麼排列畫面。

「dotfile 管理」指的是把這些散落在家目錄各處的配置檔**集中到一個 Git repo**，建立版本歷史、可以跨機器同步、可以在新環境一鍵部署。跟手動備份的差異在於：備份是搬檔案，dotfile 管理是建立一套可重複執行的環境建構流程。

## 為什麼要管理 Dotfile

開發環境是累積出來的。今天加一個 alias、明天改一個 Git 設定、下週裝了一個 terminal 外掛調了字型。這些微調加起來就是「你順手的工作環境」，但因為都是零碎的小改動，很少有人會主動記錄。

問題在累積到一定程度後、環境需要重建的那一刻才會浮出來：

**換機器**。拿到新筆電，開始從零設定。裝完 shell、editor、terminal，發現少了一堆 alias 和 function，但想不起來之前到底加了哪些。花兩天勉強恢復到七八成，剩下的在未來幾週慢慢「撞到才發現少了」。

**設備故障或遺失**。公司配的筆電硬碟壞了。如果配置沒有外部副本，那台機器上所有的自訂設定（有些可能花了半年慢慢調出來的）全部歸零。復原速度直接取決於「你有沒有把配置存在機器以外的地方」。

**在 VM 或容器裡重現環境**。想在虛擬機裡測試一套 Linux 桌面（例如 Hyprland），或在 Docker 容器裡重現自己的 shell 環境做 CI 除錯。沒有版控的配置，就得手動複製貼上，還要記住哪些檔案在哪個路徑。

**跨機器一致性**。同時用筆電、桌機、遠端伺服器，希望每台機器的 shell 行為、Git 設定、editor 快捷鍵都一致。手動同步的成本隨機器數量線性增長，而且很容易漏改某一台，導致操作習慣在不同機器間不一致。

這些場景的共通點是：**配置的價值在累積，但累積的前提是有記錄**。沒有記錄的累積，只是暫存在某一台機器上的隱性知識，機器一換就歸零。

## 哪些東西應該建立 Dotfile

依配置的普遍性和適用場景，分成三層來判斷：

### 核心層：幾乎所有開發者都該管的

- **Shell 配置**（`.zshrc` / `.bashrc`）：alias、function、PATH、prompt、completion 設定。這是最高頻修改、也最容易累積隱性知識的地方。
- **Git 配置**（`.gitconfig`）：使用者名稱、email、預設 editor、alias（`git lg` = `git log --oneline --graph`）、diff/merge tool。
- **SSH 配置**（`.ssh/config`）：Host 別名、ProxyJump 跳板設定、每台主機的 IdentityFile 指定。注意：**config 檔進 repo，私鑰不進 repo**。
- **Editor 配置**：`.vimrc`（Vim）、`~/.config/nvim/`（Neovim）、VS Code 的 `settings.json` / `keybindings.json`。

### 工具層：依個人工具鏈而定

- **Terminal multiplexer**：tmux（`.tmux.conf`）、zellij（`~/.config/zellij/`）的面板配置、快捷鍵、狀態列。
- **Terminal emulator**：Alacritty、WezTerm、Kitty 的字型、配色、快捷鍵設定。
- **套件清單**：macOS 的 `Brewfile`（`brew bundle dump`）、Arch 的 `pacman -Qqe > pkglist.txt`。這份清單讓新機器知道該裝哪些軟體。
- **開發工具的全域配置**：`.npmrc`、`.cargo/config.toml`、`.pypirc` 等。但要注意區分：`.eslintrc` / `.prettierrc` 這類通常跟著**專案** repo 走（每個專案可能規則不同），不跟著人走。

### 桌面層：Linux 桌面環境才需要

- **Window manager**：Hyprland（`~/.config/hypr/`）、i3（`~/.config/i3/`）、sway 的配置。
- **桌面元件**：狀態列（waybar）、應用程式啟動器（rofi / wofi）、通知服務（mako / dunst）、鎖屏（swaylock / hyprlock）。
- **主題與配色**：GTK / Qt 主題設定、游標主題、字型配置。

### 判讀準則

區分一個配置該不該進 dotfile repo，核心問題是：**這個設定是跟著人走，還是跟著專案走？**

跟著人走的（不管開哪個專案都要用的）→ 進 dotfile repo。跟著專案走的（專案 A 用 ESLint、專案 B 用 Biome）→ 留在專案 repo。

這個判準管的是配置該放哪個 repo。有個相鄰但不同的失敗要另外注意：**一個全域使用的工具，它的來源 / binary 若寄居在某個別專案的 checkout 裡**（例如把 CLI 用 `--from ~/project/foo/tools/bar` 這種本地路徑安裝），它就有一條隱藏的 sibling-project 依賴——換機器時那個專案不在，工具就裝不回來，重建鏈斷在那個 checkout。全域工具的來源要能獨立取得（發佈的套件、獨立 repo、或收進 dotfile），不綁在另一個專案的目錄上。

### 不該進 Dotfile Repo 的

- **私鑰、API key、token、密碼**。用 `.gitignore` 排除，敏感資訊放 secret manager 或加密管理（具體做法見[同步與 Secret 管理](/linux/dotfile/08-sync-bootstrap/sync-strategy-secret/)）。
- **暫存檔、cache、log**。`.zsh_history` 很大且含敏感指令；各種工具的 cache 目錄是 generated 檔案，重建時自動產生。
- **OS 層級的二進位設定**。macOS 的 plist 可以選擇性管理（`defaults write` 指令可以版控），但整個 `~/Library/Preferences/` 不適合直接丟進 Git——檔案格式不穩定、diff 不可讀、很多是應用程式自動產生的。
