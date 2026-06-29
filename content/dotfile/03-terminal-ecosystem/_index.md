---
title: "模組三：終端機與編輯器"
date: 2026-06-29
description: "終端機相關工具的配置檔散落在不同位置、不確定哪些該進 dotfile repo 時回來讀"
tags: ["dotfile", "terminal", "tmux", "neovim"]
---

終端機生態的配置檔數量比 shell 更多、散落位置更廣。Terminal emulator、multiplexer（tmux/zellij）、editor（neovim/vim）各自有獨立的配置體系，加上字型、配色這些跨工具共用的視覺設定，整層的管理複雜度比 shell 配置高一個量級。

## Terminal Emulator 配置

Terminal emulator 是你看到的那個「視窗」本身——字型渲染、配色、透明度、快捷鍵、分頁行為。常見的選擇和它們的配置檔位置：

| Terminal         | OS            | 配置格式          | 配置路徑                             |
| ---------------- | ------------- | ----------------- | ------------------------------------ |
| Alacritty        | 跨平台        | TOML              | `~/.config/alacritty/alacritty.toml` |
| Kitty            | 跨平台        | 自定義 key=value  | `~/.config/kitty/kitty.conf`         |
| WezTerm          | 跨平台        | Lua               | `~/.config/wezterm/wezterm.lua`      |
| iTerm2           | macOS         | plist（GUI 設定） | 可匯出 JSON profile                  |
| Foot             | Linux/Wayland | INI               | `~/.config/foot/foot.ini`            |
| Windows Terminal | Windows       | JSON              | 特定路徑下的 settings.json           |

Dotfile 管理的判讀：配置格式是純文字（TOML/Lua/INI/JSON）的 terminal emulator，配置檔可以直接進 dotfile repo。iTerm2 這種以 GUI 面板為主的，要用它的匯出功能另外處理。

選型建議：如果跨 macOS + Linux 雙平台，Alacritty 或 WezTerm 的「一份配置兩邊通用」是明確優勢。如果只在 Linux 上用 Wayland，Foot 是輕量首選。

### 該放進配置的核心項目

- **字型**：字型家族、大小、行高。建議使用 Nerd Font（含 icon glyph 的程式字型），很多 TUI 工具和 prompt 依賴這些 glyph
- **配色**：前景/背景色、ANSI 16 色的定義。配色方案（Catppuccin、Tokyo Night、Gruvbox 等）通常有各 terminal 的預設配置檔可直接套用
- **快捷鍵**：分頁/分割畫面的快捷鍵。注意跟 tmux/zellij 的快捷鍵衝突問題
- **渲染**：GPU 加速、字型 hinting、抗鋸齒設定

## Multiplexer：tmux vs zellij

Multiplexer 在一個終端機視窗裡切分多個 pane、管理多個 session、SSH 斷線後保持 session 存活。

### tmux

tmux 是最成熟、生態最廣的選擇。配置在 `~/.config/tmux/tmux.conf`（新版）或 `~/.tmux.conf`（傳統位置）。

核心配置項目：

```bash
# prefix key（預設是 Ctrl-b，很多人改成 Ctrl-a）
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# 分割 pane 的快捷鍵（預設不直覺，改成 | 和 -）
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"

# 用 vim 風格的 hjkl 切換 pane
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# 啟用滑鼠支援
set -g mouse on

# 256 色支援
set -g default-terminal "tmux-256color"
set -ag terminal-overrides ",xterm-256color:RGB"

# status bar 位置
set -g status-position top
```

tmux plugin 用 TPM（Tmux Plugin Manager）管理，常用：

- **tmux-sensible**：合理的預設值
- **tmux-resurrect**：重開機後還原 session 佈局
- **tmux-continuum**：自動儲存 session

### zellij

zellij 是較新的替代品，Rust 寫的，內建佈局系統、tab 命名、浮動 pane。配置在 `~/.config/zellij/config.kdl`（KDL 格式）。

跟 tmux 的主要差異：

- 開箱即用的 UI 提示（底部顯示可用快捷鍵），學習曲線較低
- 佈局用 KDL 宣告式描述，比 tmux 的 script 式設定更容易管理
- Plugin 系統用 WASM，跟 tmux 的 bash script 式 plugin 不同
- 生態較新、plugin 和整合沒有 tmux 多

選型：已經熟 tmux 的人通常沒有強烈理由遷移；從零開始的人 zellij 的上手成本更低。

## Neovim 配置

Neovim 的配置是 dotfile 裡最複雜的單一工具——plugin 生態龐大、Lua 配置可以寫成一個完整的小專案。

配置路徑：`~/.config/nvim/`

### 配置結構

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

### 是否該用預設配置包

LazyVim、NvChad、AstroNvim 這類預設配置包提供了一整套開箱即用的 neovim 設定。判讀：

- **用預設配置包**：想要快速可用的 IDE-like 體驗、不想花時間逐一選 plugin 和配置。Dotfile 裡放的是「對預設的覆寫」
- **自己從零組**：想完全理解每一個 plugin 做什麼、容忍前期投入時間。Dotfile 裡放的是完整配置

兩種都是 dotfile 管理的合法對象。差異在出問題時的除錯路徑：自己組的知道每一行做什麼，預設配置包的要先理解它的分層才能改。

## 配色系統的跨工具一致性

配色方案（color scheme）會同時影響 terminal emulator、editor、tmux status bar、shell prompt。用同一套配色方案（例如 Catppuccin Mocha）跨工具統一視覺是 rice 的基礎。

管理方式：

- 每個工具各自的配色設定檔都放進 dotfile repo
- 主題選擇集中記錄（例如 dotfile repo 的 README 寫「全域使用 Catppuccin Mocha」），換主題時有對照清單知道要改哪些檔案
- 部分配色方案提供「一鍵安裝腳本」涵蓋多個工具，也可以放在 bootstrap script 裡

## 字型管理

Nerd Font 是需要安裝在系統上的，不是單純的配置檔。處理方式：

- macOS：Brewfile 裡加 `cask "font-hack-nerd-font"`（透過 homebrew-cask-fonts tap）
- Linux：套件管理器安裝或手動下載到 `~/.local/share/fonts/`
- 字型檔案本身不進 dotfile repo（太大、有版權），只記錄「安裝哪個字型」在套件清單或 bootstrap script 裡

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
