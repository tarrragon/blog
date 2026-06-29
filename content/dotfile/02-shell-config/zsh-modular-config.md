---
title: "Zsh 模組化配置"
date: 2026-06-29
description: ".zshrc 長到數百行不敢動時回來讀 — zsh/bash 載入順序、.zshrc 只做 source 的拆分結構、alias/function/tools/local 各模組的職責"
weight: 1
tags: ["dotfile", "shell", "zsh", "bash"]
---

Shell 配置是 dotfile 管理裡最基礎也最常失控的一層。`.zshrc` 或 `.bashrc` 通常是開發者第一個開始客製的檔案，也是最容易長成數百行無結構巨檔的對象。

## Zsh vs Bash 的配置檔載入順序

理解配置檔的載入順序是結構化拆分的前提。不知道哪個檔案在什麼時機被讀取，就無法判斷設定該放在哪。

### Bash 的載入順序

Bash 區分 login shell 和 non-login shell，兩者讀取的檔案不同：

- **Login shell**（SSH 進來、`bash --login`）：讀 `~/.bash_profile`（如果不存在，依序嘗試 `~/.bash_login` → `~/.profile`）
- **Non-login interactive shell**（開一個新終端機視窗）：讀 `~/.bashrc`
- 常見做法：在 `~/.bash_profile` 裡 source `~/.bashrc`，確保設定不管怎麼進來都一致

### Zsh 的載入順序

Zsh 的載入鏈比 Bash 更細緻：

1. `~/.zshenv` — 每次都讀（login、non-login、script 都會），放環境變數
2. `~/.zprofile` — 只有 login shell 讀，對應 Bash 的 `~/.bash_profile`
3. `~/.zshrc` — interactive shell 讀，放 alias、function、prompt、plugin
4. `~/.zlogin` — login shell 在 `.zshrc` 之後讀（少用）
5. `~/.zlogout` — logout 時讀（少用）

實務上 90% 的設定都進 `.zshrc`，環境變數（`PATH`、`EDITOR`）放 `.zshenv`。

## 結構化拆分：從單一巨檔到模組化

一個典型的失控 `.zshrc` 長這樣：PATH 設定、alias、function、plugin 載入、prompt 配置、各種工具的 eval/source 全混在一起，改一個東西要在五百行裡找位置。

模組化的目標是依職責拆檔，`.zshrc` 本身只負責 source 這些模組：

```bash
# ~/.zshrc — 只做 source，不放具體設定

# 環境變數（PATH 在 .zshenv，這裡放其他 interactive 專用的）
source "$HOME/.config/zsh/env.zsh"

# Alias
source "$HOME/.config/zsh/aliases.zsh"

# Function
source "$HOME/.config/zsh/functions.zsh"

# Plugin manager
source "$HOME/.config/zsh/plugins.zsh"

# Prompt / theme
source "$HOME/.config/zsh/prompt.zsh"

# 工具整合（fzf, nvm, pyenv, etc.）
source "$HOME/.config/zsh/tools.zsh"

# 機器專屬設定（不進 Git）
[[ -f "$HOME/.config/zsh/local.zsh" ]] && source "$HOME/.config/zsh/local.zsh"
```

## 各模組的職責

### aliases.zsh — 短指令對映

```bash
# 檔案操作
alias ll='ls -alF'
alias la='ls -A'

# Git 常用
alias gs='git status'
alias gd='git diff'
alias gco='git checkout'
alias gp='git push'

# 導航
alias ..='cd ..'
alias ...='cd ../..'
```

判讀準則：alias 適合「不帶參數的簡單替換」。如果需要參數處理或條件判斷，改用 function。

### functions.zsh — 帶邏輯的常用操作

```bash
# 建目錄並進入
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# 在 Git repo 根目錄搜尋
ggrep() {
    git grep "$@" "$(git rev-parse --show-toplevel)"
}
```

### tools.zsh — 第三方工具的初始化

```bash
# fzf
[[ -f ~/.fzf.zsh ]] && source ~/.fzf.zsh

# nvm
export NVM_DIR="$HOME/.nvm"
[[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"

# pyenv
command -v pyenv >/dev/null && eval "$(pyenv init -)"
```

每個工具的 init 前面加存在性檢查（`command -v` 或 `[[ -f ]]`），避免在沒裝該工具的機器上報錯。

### local.zsh — 機器專屬、不進 Git

```bash
# 公司 VPN 設定
export CORP_PROXY="http://proxy.corp:8080"

# 只有這台機器需要的 PATH
export PATH="$HOME/corp-tools/bin:$PATH"
```

在 dotfile repo 的 `.gitignore` 裡排除這個檔案。`.zshrc` 裡用 `[[ -f ... ]] && source` 確保不存在也不報錯。
