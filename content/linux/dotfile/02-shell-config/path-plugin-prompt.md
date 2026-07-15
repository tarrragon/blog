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

### PATH 可能被安裝器寫進非-repo 的檔案

上面把 PATH 當成集中宣告的東西。但有一類 PATH 設定不是自己寫的：安裝器（Homebrew、rustup、nvm、conda）裝完後，常往 `~/.bashrc`、`~/.zprofile`、`~/.profile` 尾端 append 一行 init 或 PATH；官方 `.pkg` / 套件則丟 `/etc/paths.d/`（macOS）或 `/etc/profile.d/`（Linux）的系統檔。

這些檔案多半不在 dotfile repo 的追蹤範圍。結果是：工具在原機上叫得動（那行被 append 過），換一台乾淨機器、dotfile 部署完之後，工具裝了、shell 卻 command not found——那行 init 沒被 repo 收錄。處理方式二選一：把安裝器寫的那行搬進自己管理的 `env.zsh`（重新宣告、由 repo 控制），或把對應 profile 收進 dotfile。安裝器輸出的「請把這行加進 `~/.bashrc`」就是一條未宣告依賴，見 [乾淨機器驗證](/linux/dotfile/00-dotfile-mindset/clean-machine-verification/)。

### PATH 改動的三個作用域

`export PATH=...` 只影響「執行這行的那個 shell 行程」。這帶出 bootstrap 常踩的陷阱：子行程改的 PATH 回不到父行程。

bootstrap script 常分層——`install.sh` 呼叫 `install-<platform>.sh`，後者裝完套件管理器後 `eval "$(brew shellenv)"` 把 PATH 補上。但那個 eval 只改了子 script 自己的 PATH；控制權回到 `install.sh`（父行程）的共通層時 PATH 又沒了，下一步用到剛裝的工具就 command not found。同一個 PATH gap 要在三個作用域各補一次：

| 作用域                | 誰需要                           | 怎麼補                                              |
| --------------------- | -------------------------------- | --------------------------------------------------- |
| 當前 bootstrap 子行程 | 子 script 裝完工具後立刻要用     | 子 script 內 `eval shellenv` / 補 PATH              |
| 父 orchestrator 行程  | 父 script 後續共通層要用同一工具 | 父 script 自己也 eval 一次（子行程改動不上傳）      |
| 未來的互動 shell      | 使用者開新 terminal 要用         | 寫進 dotfile 管理的 init（`env.zsh` / `.zprofile`） |

漏掉任一個，症狀都是「這個 script 段落 command not found」，根因是那個作用域沒拿到 PATH。

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

[管理工具與目錄結構](/linux/dotfile/01-dotfile-management/)裡的 stow 目錄結構，shell 配置的對應：

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
