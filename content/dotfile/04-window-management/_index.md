---
title: "模組四：視窗管理與自動平鋪"
date: 2026-06-29
description: "同時開多個視窗時的排列策略 — 手動貼齊跟自動平鋪的差距在哪、macOS 和 Linux 各有哪些工具、多螢幕怎麼處理、什麼情境值得從浮動切換到平鋪"
weight: 4
tags: ["dotfile", "window-manager", "tiling", "hyprland", "workflow"]
---

視窗管理器（window manager, WM）負責決定螢幕上的視窗怎麼排列、怎麼切換、怎麼調整大小。每個桌面環境都有一個 WM，差別在於它是讓你用滑鼠自己拖，還是按規則自動幫你排好。

## 章節文章

| 文章                                                                      | 主題                                                              |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [浮動式 vs 平鋪式](/dotfile/04-window-management/floating-vs-tiling/)     | 兩種視窗管理模式的差異、手動貼齊 vs 自動平鋪的三層差距、適用判讀  |
| [macOS 視窗管理工具鏈](/dotfile/04-window-management/macos-window-tools/) | Rectangle / Amethyst / AeroSpace / yabai 選型判讀與配置範例       |
| [Linux Tiling WM 生態](/dotfile/04-window-management/linux-tiling-wm/)    | Wayland vs X11、主流 tiling WM 比較、多螢幕處理、dotfile 中的角色 |

## 跨分類引用

- → [模組五：Hyprland 配置](/dotfile/05-hyprland-config/)：Hyprland 的完整配置實務
- → [模組六：桌面 Rice 設計](/dotfile/06-rice-design/)：compositor 之上的狀態列、啟動器、通知、配色系統
- → [模組一：管理工具與目錄結構](/dotfile/01-dotfile-management/)：WM 配置怎麼進 dotfile repo
- → [模組七：同步、Bootstrap 與環境重建](/dotfile/07-sync-bootstrap/)：跨機器搬移時硬體相關設定怎麼處理
