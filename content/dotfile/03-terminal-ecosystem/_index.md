---
title: "模組三：終端機與編輯器"
date: 2026-06-29
description: "終端機相關工具的配置檔散落在不同位置、不確定哪些該進 dotfile repo 時回來讀"
weight: 3
tags: ["dotfile", "terminal", "tmux", "neovim"]
---

終端機生態的配置檔數量比 shell 更多、散落位置更廣。Terminal emulator、multiplexer（tmux/zellij）、editor（neovim/vim）各自有獨立的配置體系，加上字型、配色這些跨工具共用的視覺設定，整層的管理複雜度比 shell 配置高一個量級。

## 章節文章

| 文章                                                                                                  | 主題                                                   |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| [Terminal Emulator 配置](/dotfile/03-terminal-ecosystem/terminal-emulator-config/)                     | 常見 terminal emulator 選型、配置判讀、配色與字型管理  |
| [Multiplexer：tmux vs zellij](/dotfile/03-terminal-ecosystem/multiplexer-tmux-zellij/)                | tmux 和 zellij 的配置、plugin、選型判讀                |
| [Neovim 配置](/dotfile/03-terminal-ecosystem/neovim-config/)                                          | neovim 配置結構、預設配置包判讀、dotfile 結構對應      |

## 跨分類引用

- → [模組二：Shell 配置](/dotfile/02-shell-config/)：shell 是終端機工具的載體，配置拆分邏輯相通
- → [模組六：桌面 Rice 設計](/dotfile/06-rice-design/)：配色系統的統一管理從 terminal 延伸到桌面
