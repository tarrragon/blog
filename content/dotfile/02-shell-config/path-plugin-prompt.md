---
title: "PATH、Plugin 與 Prompt"
date: 2026-06-29
description: "PATH 越來越長不知道怎麼管、要選 zsh plugin manager、或想設計 prompt 時回來讀"
weight: 2
tags: ["dotfile", "shell", "zsh", "path"]
---

PATH、plugin manager 和 prompt 是 shell 配置裡「每個開發者都會碰到、但容易放任不管」的三個區域。

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

[管理工具與目錄結構](/dotfile/01-dotfile-management/)裡的 stow 目錄結構，shell 配置的對應：

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
