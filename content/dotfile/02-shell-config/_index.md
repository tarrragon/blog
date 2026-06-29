---
title: "模組二：Shell 配置"
date: 2026-06-29
description: "shell 配置檔長成一坨不敢動時回來讀 — .zshrc/.bashrc 的結構化拆分、alias/function/PATH 的模組化設計"
tags: ["dotfile", "shell", "zsh", "bash"]
---

Shell 配置是 dotfile 管理裡最基礎也最常失控的一層。`.zshrc` 或 `.bashrc` 通常是開發者第一個開始客製的檔案，也是最容易長成數百行無結構巨檔的對象。這個模組教的是怎麼把 shell 配置拆成可維護的模組化結構。

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

### 各模組的職責

**aliases.zsh** — 短指令對映

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

**functions.zsh** — 帶邏輯的常用操作

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

**tools.zsh** — 第三方工具的初始化

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

**local.zsh** — 機器專屬、不進 Git

```bash
# 公司 VPN 設定
export CORP_PROXY="http://proxy.corp:8080"

# 只有這台機器需要的 PATH
export PATH="$HOME/corp-tools/bin:$PATH"
```

在 dotfile repo 的 `.gitignore` 裡排除這個檔案。`.zshrc` 裡用 `[[ -f ... ]] && source` 確保不存在也不報錯。

## PATH 管理

PATH 是最容易腐化的環境變數——每裝一個工具就加一條，最後 PATH 變成一長串看不懂的路徑，順序還會互相影響。

管理原則：

- PATH 設定集中在一個地方（`.zshenv` 或 `env.zsh`），不散落在多個檔案
- 新增前先想：這個路徑是所有機器都需要、還是特定機器才需要？共用的進 env.zsh，特定的進 local.zsh
- 用 `typeset -U PATH` (Zsh) 自動去除重複項目，避免多次 source 導致 PATH 不斷加長

```bash
# ~/.config/zsh/env.zsh
typeset -U PATH  # 去重

# 自己的 script
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/bin:$PATH"
```

## Plugin Manager 選型

Zsh plugin manager 的選擇很多，差異主要在載入速度和功能豐富度：

- **無 plugin manager**：直接 git clone plugin 到某個目錄，手動 source。最簡單、最透明、但更新要自己管
- **zinit**（原 zplugin）：載入速度最快（turbo mode 延遲載入）、功能最多、但配置語法學習曲線高
- **antidote**：宣告式（一個 `.zsh_plugins.txt` 列出所有 plugin），概念簡單
- **sheldon**：Rust 寫的、速度快、設定用 TOML

常用 plugin：

- **zsh-autosuggestions**：根據歷史指令自動補全建議（灰色字，按右箭頭接受）
- **zsh-syntax-highlighting**：指令行即時語法高亮
- **zsh-completions**：額外的 tab 補全定義

## Prompt 設計

Prompt 是每次按 Enter 都會看到的東西，值得花時間設計但不需要複雜。

基本款（不用框架）：

```bash
# 顯示目錄 + git branch
autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats ' (%b)'
PROMPT='%F{blue}%~%f%F{green}${vcs_info_msg_0_}%f %# '
```

框架款：Starship（跨 shell、用 TOML 設定、Rust 寫的速度快）是目前最常被推薦的 prompt 工具。它的配置進 `~/.config/starship.toml`，也是 dotfile 的一部分。

## Dotfile 結構對應

模組一的 stow 目錄結構裡，shell 配置的對應：

```text
~/dotfiles/
└── zsh/
    ├── .zshenv
    ├── .zshrc
    └── .config/
        └── zsh/
            ├── aliases.zsh
            ├── functions.zsh
            ├── plugins.zsh
            ├── prompt.zsh
            ├── tools.zsh
            └── env.zsh
```

`stow zsh` 會在家目錄建立 `.zshenv` 和 `.zshrc` 的 symlink，在 `.config/zsh/` 下建立各模組檔案的 symlink。`local.zsh` 不在 repo 裡，各機器自己建。
