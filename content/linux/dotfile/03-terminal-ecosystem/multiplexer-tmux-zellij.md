---
title: "Multiplexer：tmux vs zellij"
date: 2026-06-29
description: "在終端機裡切分 pane、管理多個 session、SSH 斷線後保持工作時回來讀 — tmux 和 zellij 的配置與選型"
weight: 2
tags: ["dotfile", "tmux", "zellij", "terminal"]
---

Multiplexer 在一個終端機視窗裡切分多個 pane、管理多個 session、SSH 斷線後保持 session 存活。

## tmux

tmux 是最成熟、生態最廣的選擇。配置在 `~/.config/tmux/tmux.conf`（新版）或 `~/.tmux.conf`（傳統位置）。

### 核心配置項目

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

### tmux plugin

用 TPM（Tmux Plugin Manager）管理，常用：

- **tmux-sensible**：合理的預設值
- **tmux-resurrect**：重開機後還原 session 佈局
- **tmux-continuum**：自動儲存 session

## zellij

zellij 是較新的替代品，Rust 寫的，內建佈局系統、tab 命名、浮動 pane。配置在 `~/.config/zellij/config.kdl`（KDL 格式）。

跟 tmux 的主要差異：

- 開箱即用的 UI 提示（底部顯示可用快捷鍵），學習曲線較低
- 佈局用 KDL 宣告式描述，比 tmux 的 script 式設定更容易管理
- Plugin 系統用 WASM，跟 tmux 的 bash script 式 plugin 不同
- 生態較新、plugin 和整合沒有 tmux 多

## 選型判讀

已經熟 tmux 的人通常沒有強烈理由遷移；從零開始的人 zellij 的上手成本更低。

## 深入

這篇是多工器的概覽（在終端機生態裡的定位、tmux 與 zellij 的取捨）。把它們當「遠端工作工具」深入用——session 持久化的核心概念、遠端斷線接回、瀏覽器連遠端 session——見工具選單的深度頁：

- [tmux 持久化與基礎](/linux/tools/cli/tmux-persistence-and-basics/)——session 持久化怎麼保住遠端工作。
- [zellij 分頁與 pane](/linux/tools/cli/zellij-pane/)——內建佈局的操作深入。
- [zellij 遠端 web 客戶端](/linux/tools/cli/zellij-remote-web-client/)——從瀏覽器連遠端 session。
- [遠端連線與同步工具選型](/linux/tools/remote/connection-and-sync-tools/)——多工器之外的連線（mosh/autossh）與同步（rsync/sshfs/mutagen）。
