---
title: "Terminal Emulator 配置"
date: 2026-06-29
description: "選 terminal emulator 時需要比對配置格式和跨平台能力、或想把配色和字型統一管理時回來讀"
weight: 1
tags: ["dotfile", "terminal", "alacritty", "kitty", "wezterm"]
---

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

## 該放進配置的核心項目

- **字型**：字型家族、大小、行高。建議使用 Nerd Font（含 icon glyph 的程式字型），很多 TUI 工具和 prompt 依賴這些 glyph
- **配色**：前景/背景色、ANSI 16 色的定義。配色方案（Catppuccin、Tokyo Night、Gruvbox 等）通常有各 terminal 的預設配置檔可直接套用
- **快捷鍵**：分頁/分割畫面的快捷鍵。注意跟 tmux/zellij 的快捷鍵衝突問題
- **渲染**：GPU 加速、字型 hinting、抗鋸齒設定

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

安裝字型後如果畫面仍然顯示豆腐方塊，原因通常是顯示它的程式在字型安裝之前就已啟動，跟字型有沒有裝好無關。每個 process 的可用字型集合在啟動時決定，之後新裝的字型對它不可見——需要重啟該程式才生效。詳見 [字型的可用集合在 process 啟動時決定](/linux/dotfile/knowledge-cards/font-availability-at-startup/)。fontconfig 的工具分工與 fallback 機制見 [fontconfig](/linux/dotfile/knowledge-cards/fontconfig/)。
