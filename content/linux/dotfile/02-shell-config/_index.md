---
title: "模組二：Shell 配置"
date: 2026-06-29
description: "shell 配置檔長到雜亂不敢動時回來讀 — .zshrc/.bashrc 的結構化拆分、alias/function/PATH 的模組化設計"
weight: 2
tags: ["dotfile", "shell", "zsh", "bash"]
---

Shell 配置是 dotfile 管理裡最基礎也最常失控的一層。`.zshrc` 或 `.bashrc` 通常是開發者第一個開始客製的檔案，也是最容易長成數百行無結構巨檔的對象。這個模組教的是怎麼把 shell 配置拆成可維護的模組化結構。

## 章節文章

| 文章                                                                         | 主題                                                                  |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [Zsh 模組化配置](/linux/dotfile/02-shell-config/zsh-modular-config/)         | zsh/bash 載入順序、.zshrc 只做 source 的拆分結構、各模組的職責        |
| [PATH、Plugin 與 Prompt](/linux/dotfile/02-shell-config/path-plugin-prompt/) | PATH 管理原則、plugin manager 選型、prompt 設計、dotfile 目錄結構對應 |

## 跨分類引用

- → [模組一：管理策略](/linux/dotfile/01-dotfile-management/management-strategies/)：stow 的 package 概念怎麼對應 shell 配置的目錄結構
- → [模組一：跨平台共用一個 Repo](/linux/dotfile/01-dotfile-management/cross-platform-one-repo/)：path.zsh 和 tools.zsh 裡的 OS 分流做法
- → [模組三：終端機與編輯器](/linux/dotfile/03-terminal-ecosystem/)：terminal emulator 的配色跟 shell prompt 的配色協調
