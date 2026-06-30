---
title: "環境建置的操作順序"
date: 2026-06-30
description: "第一次從零建立 Linux 或 macOS 開發環境、不確定先做什麼後做什麼時讀 — 依賴順序路線圖，每一步附對應模組連結"
weight: 3
tags: ["dotfile", "workflow", "bootstrap", "ssh"]
---

Dotfile 教學模組按主題組織（shell、終端機、視窗管理），適合理解各層概念。但第一次建環境時需要的是另一種順序——**按依賴關係排列的操作清單**，因為有些步驟是後續步驟的前提。

SSH key 是典型例子：管理工具和 shell 配置的知識在模組一和模組二，但實際操作時 SSH key 比這兩者都早——因為 `git clone git@github.com:...` 本身就需要 SSH key。如果照模組順序走，到模組二才發現 dotfile repo clone 不下來。

這篇是路線圖，告訴你每一步做什麼、為什麼這個順序、以及去哪個模組看具體操作。

## 階段一：基礎設施（後續所有步驟的前提）

這些步驟在任何配置之前完成，因為它們是 Git、遠端存取、dotfile clone 的前提。

### 1. 安裝作業系統 + 建立使用者帳號

macOS：開箱即用。Linux：選發行版（Arch 如果要用 Hyprland）、完成安裝、建立非 root 使用者。

### 2. 生成 SSH key pair

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

為什麼這麼早做：

- **Git 操作**：GitHub / GitLab 的 SSH 認證需要 public key。dotfile repo 通常用 SSH URL（`git@github.com:...`），clone 前要先把 key 部署到 GitHub。用 HTTPS URL 可以繞過 SSH key，但長期來看 SSH key 是更省事的認證方式。
- **遠端救援**：[模組七](/dotfile/07-desktop-maintenance/)的場景三（GPU hang）依賴 SSH 作為桌面凍結時的救生通道。key 提前設好，出問題時才有路可走。
- **跨機器操作**：筆電連桌機、桌機連 VM、VS Code Remote SSH——都靠這把 key。

### 3. 部署 public key

把 `~/.ssh/id_ed25519.pub` 加到需要的服務：

```bash
# 加到 GitHub
cat ~/.ssh/id_ed25519.pub
# 複製輸出，貼到 GitHub → Settings → SSH and GPG keys → New SSH key

# 加到另一台機器（可選，用於跨機器 SSH）
ssh-copy-id user@target-machine
```

### 4. Package manager + Git

macOS：先裝 Homebrew（macOS 的套件管理器，後續安裝 stow、tmux 等工具都靠它），再裝 Git：

```bash
# 安裝 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 Git（或用 xcode-select --install，會一併裝 Apple 的 Git）
brew install git
```

Arch：`pacman` 隨 OS 安裝已可用，直接裝 Git：`pacman -S git`。

### 5. Clone dotfile repo

```bash
git clone git@github.com:yourname/dotfiles.git ~/dotfiles
```

如果是第一次建 dotfile repo（還沒有 repo），先建一個空的再開始往裡面加配置。具體做法見[模組一：管理工具與目錄結構](/dotfile/01-dotfile-management/)。

## 階段二：Shell 與終端機（日常操作的基礎）

Shell 是所有操作的介面，終端機是 shell 的容器。這兩層配置好，後續的安裝、設定、除錯效率會高很多。

### 6. 安裝管理工具（stow / chezmoi）

把 dotfile repo 裡的配置 symlink 到正確位置。具體選型和操作見[模組一](/dotfile/01-dotfile-management/)。

### 7. Shell 配置（.zshrc / .bashrc）

模組化拆分、PATH 設定、alias、prompt。做完這一步，終端機操作才順手。見[模組二：Shell 配置](/dotfile/02-shell-config/)。

### 8. 終端機 + 編輯器

Terminal emulator 選型、tmux/zellij、neovim 基礎配置。見[模組三：終端機與編輯器](/dotfile/03-terminal-ecosystem/)。

macOS 用戶到階段二完成後就有一個完整的工作環境。下一步依序讀[模組一](/dotfile/01-dotfile-management/)（管理工具選型）、[模組二](/dotfile/02-shell-config/)（shell 配置）、[模組三](/dotfile/03-terminal-ecosystem/)（終端機），然後跳到階段四的 bootstrap script。階段三是 Linux 桌面環境的設定，macOS 用戶跳過。

## 階段三：桌面環境（Linux 限定）

macOS 用戶到階段二就有一個完整的工作環境了。以下步驟是 Linux 桌面環境的設定，macOS 用戶可以跳到階段四。

### 9. 視窗管理器

平鋪式 vs 浮動式的選型，Hyprland 安裝和核心配置。見[模組四](/dotfile/04-window-management/)和[模組五](/dotfile/05-hyprland-config/)。

### 10. 桌面配套工具 + Rice

waybar、wofi、mako、配色系統。見[模組六：桌面 Rice 設計](/dotfile/06-rice-design/)。

### 11. 啟用 SSH server + 預防措施

桌面環境可用之後，設定遠端救援通道和預防性配置：

```bash
# SSH server（出問題時可以從另一台機器救援）
sudo systemctl enable sshd
sudo systemctl start sshd

# 停用密碼登入（確保 SSH key 已設好）
# 編輯 /etc/ssh/sshd_config：PasswordAuthentication no

# swap（OOM 緩衝）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile

# systemd-oomd
sudo systemctl enable systemd-oomd
```

為什麼放在桌面設定之後：SSH server 和 swap 是預防措施，桌面能用了才有東西要保護。但 SSH key pair（階段一步驟 2-3）要提前做——key pair 是認證基礎設施，server 只是把門打開。

詳細的故障場景和預防措施見[模組七：桌面環境維護與故障排除](/dotfile/07-desktop-maintenance/)。

## 階段四：同步與可攜性

環境建好之後，確保這份配置能搬到下一台機器。

### 12. Bootstrap script

把階段一到三的操作自動化成 script，下次換機器跑一次就好。見[模組八：同步、Bootstrap 與環境重建](/dotfile/08-sync-bootstrap/)。

### 13. Secret 管理

哪些東西該進 repo、哪些要排除（SSH private key、API token、密碼）。同樣見[模組八](/dotfile/08-sync-bootstrap/)。

## 依賴關係速查

```text
OS 安裝
  └─ SSH key pair ← 後續所有 Git / SSH 操作的前提
       └─ Git 安裝
            └─ dotfile repo clone
                 └─ 管理工具（stow link）
                      ├─ Shell 配置
                      ├─ 終端機 + 編輯器
                      └─ 桌面環境（Linux，macOS 到此為止 → 直接跳階段四）
                           └─ SSH server + 預防措施
                                └─ Bootstrap script 自動化
```

## 可以亂序的步驟

依賴圖裡**同一層級的步驟**可以調換順序。具體來說：

- Shell 配置、終端機配置、編輯器配置三者互不依賴，先做哪個都行
- 視窗管理器和桌面配套工具可以交替設定（先裝 Hyprland 再裝 waybar，或反過來）
- swap 和 SSH server 互不依賴，先做哪個都行

跨層級的依賴必須按順序：SSH key 是 clone repo 的前提，repo 是 stow link 的前提，stow link 是 shell 配置生效的前提。
