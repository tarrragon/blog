---
title: "模組零：Dotfile 心智模型"
date: 2026-06-29
description: "換機器、開 VM、重灌系統時需要快速還原開發環境，或想釐清哪些配置該版控、哪些該排除時回來讀"
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

## Dotfile 跟 Infra IaC 的平行關係

[Infra 基礎設施建置指南](/infra/)教的是用 Terraform 或 OpenTofu 把雲端資源（VPC、IAM role、EC2 instance）寫成代碼，讓基礎設施可重現、可 review、可回滾。Dotfile 做的事在概念上完全平行：把個人工作環境（shell、editor、terminal、window manager）寫成代碼，達成同樣的可重現性。

兩者共用的核心原則：

- **宣告式**：描述「環境應該長什麼樣」，而非「操作了哪些步驟」。Terraform 宣告「要有一個 VPC、CIDR 是 10.0.0.0/16」；dotfile 宣告「zsh 的 prompt 格式是這樣、alias ll 對應 ls -la」。
- **版控下的變更歷史**：誰改了什麼、什麼時候改的、為什麼改，都在 Git log 裡。環境出問題時可以回溯到「上一次正常的狀態」是哪個 commit。
- **可 review**：改了一個 shell function，diff 清楚可讀。跟在 terminal 裡直接 export 一個變數、下次重開就忘了相比，版控下的改動有跡可循。

差異也值得認識：

| 維度       | Infra IaC                                 | Dotfile                                      |
| ---------- | ----------------------------------------- | -------------------------------------------- |
| 管理對象   | 組織的雲端資源                            | 個人的工作桌面                               |
| State 管理 | Remote backend + lock 機制（防並行衝突）  | 通常只用 Git，沒有額外 state file            |
| 生效方式   | `terraform plan` → `terraform apply` 兩步 | 多數改完 source 即生效，或重開 terminal 生效 |
| 影響範圍   | 改錯可能影響 production 服務              | 改錯最多影響自己的工作環境                   |
| 協作需求   | 團隊共用、需要 PR review                  | 通常個人維護，PR review 是可選的             |

這個平行不只是比喻。[模組八：從個人到團隊](/dotfile/08-team-environment/)會教怎麼把 dotfile 的思想正式擴展到團隊環境——devcontainer 把「開發環境應該長什麼樣」寫成宣告式配置，讓新人 clone repo 就能拿到一致的開發環境，這正是 IaC 思想從組織 infra 往個人工作桌面延伸的具體產物。

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

### 不該進 Dotfile Repo 的

- **私鑰、API key、token、密碼**。用 `.gitignore` 排除，敏感資訊放 secret manager 或加密管理（模組七會教具體做法）。
- **暫存檔、cache、log**。`.zsh_history` 很大且含敏感指令；各種工具的 cache 目錄是 generated 檔案，重建時自動產生。
- **OS 層級的二進位設定**。macOS 的 plist 可以選擇性管理（`defaults write` 指令可以版控），但整個 `~/Library/Preferences/` 不適合直接丟進 Git——檔案格式不穩定、diff 不可讀、很多是應用程式自動產生的。

## Dotfile 是重建指令，不是備份

這是最重要的心智模型區分。Dotfile repo 的目標不是「把舊電腦的所有檔案搬到新電腦」（那是備份工具的工作），而是「一份能在空白機器上重建工作環境的指令集」。

這個思維跟 Docker 的哲學一致：Docker image 透過 Dockerfile「描述如何重建」環境，而不是「對一台跑著的伺服器拍快照」。Dotfile repo 也是——它記錄的是「你的環境應該長什麼樣」的宣告，不是「你的機器上現在有什麼」的快照。

這個區分決定了 repo 裡該放什麼：

- 放進去的：**宣告式的配置檔**（shell config、editor config、WM config）、**套件清單**（Brewfile、pacman list）、**安裝腳本**（`install.sh`，用來在新機器上自動化部署流程）。
- 不放的：**暫存狀態**（shell history、undo file、session file）、**generated 產物**（plugin 的 compiled cache）、**大型二進位檔**（字型檔案可以用套件管理器裝，不用放 repo）。

維持「重建指令」的純度，repo 才能保持輕量、diff 可讀、跨機器部署不會帶進不必要的狀態。

## 接下來

[模組一](/dotfile/01-dotfile-management/)教具體的管理工具和目錄結構：怎麼把散落在家目錄各處的配置檔收進 Git repo、目前主流的管理方案（bare repo / GNU Stow / chezmoi）各自適合什麼情境、repo 的目錄結構該怎麼設計才好維護。
