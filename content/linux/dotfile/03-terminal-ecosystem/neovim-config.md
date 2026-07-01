---
title: "Neovim 配置"
date: 2026-06-29
description: "neovim 配置該怎麼組織進 dotfile、要不要用 LazyVim 等預設配置包時回來讀"
weight: 3
tags: ["dotfile", "neovim", "editor"]
---

Neovim 的配置是 dotfile 裡最複雜的單一工具——plugin 生態龐大、整個配置系統基於 Lua。Lua 語法基礎見 [Lua 腳本語言](/linux/dotfile/knowledge-cards/lua-scripting-language/)。

配置路徑：`~/.config/nvim/`

## 配置結構

```text
~/.config/nvim/
├── init.lua              # 入口，source 其他模組
├── lua/
│   ├── options.lua       # 基本設定（行號、tab 寬度、搜尋行為）
│   ├── keymaps.lua       # 快捷鍵
│   ├── autocmds.lua      # 自動指令
│   └── plugins/          # 各 plugin 的配置
│       ├── init.lua      # plugin manager 載入
│       ├── lsp.lua       # LSP 設定
│       ├── telescope.lua # fuzzy finder
│       ├── treesitter.lua
│       └── ...
└── lazy-lock.json        # lazy.nvim 的 lockfile（要進 Git）
```

## 是否該用預設配置包

LazyVim、NvChad、AstroNvim 這類預設配置包提供了一整套開箱即用的 neovim 設定。判讀：

- **用預設配置包**：想要快速可用的 IDE-like 體驗、不想花時間逐一選 plugin 和配置。Dotfile 裡放的是「對預設的覆寫」
- **自己從零組**：想完全理解每一個 plugin 做什麼、容忍前期投入時間。Dotfile 裡放的是完整配置

兩種都是 dotfile 管理的合法對象。差異在出問題時的除錯路徑：自己組的知道每一行做什麼，預設配置包的要先理解它的分層才能改。

## Dotfile 結構對應

```text
~/dotfiles/
├── alacritty/
│   └── .config/
│       └── alacritty/
│           └── alacritty.toml
├── tmux/
│   └── .config/
│       └── tmux/
│           └── tmux.conf
├── nvim/
│   └── .config/
│       └── nvim/
│           ├── init.lua
│           ├── lazy-lock.json
│           └── lua/
│               └── ...
└── zellij/                    # 如果用 zellij
    └── .config/
        └── zellij/
            └── config.kdl
```

每個工具是獨立的 stow package，可以在不同機器選擇性安裝。例如伺服器只 `stow tmux nvim`、桌面機才加 `stow alacritty`。
