---
title: "模組四：視窗管理與平鋪式工作流"
date: 2026-06-29
description: "同時開多個視窗時的排列策略 — 手動貼齊跟自動平鋪的差距在哪、macOS 和 Linux 各有哪些工具、多螢幕怎麼處理、什麼情境值得從浮動切換到平鋪"
weight: 4
tags: ["dotfile", "window-manager", "tiling", "hyprland", "workflow"]
---

視窗管理器（window manager, WM）負責決定螢幕上的視窗怎麼排列、怎麼切換、怎麼調整大小。每個桌面環境都有一個 WM，差別在於它是讓你用滑鼠自己拖，還是按規則自動幫你排好。

## 章節文章

| 文章                                                                            | 主題                                                                                     |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [浮動式 vs 平鋪式](/linux/dotfile/04-window-management/floating-vs-tiling/)     | 兩種視窗管理模式的差異、手動貼齊 vs 自動平鋪的三層差距、適用判讀                         |
| [macOS 視窗管理工具鏈](/linux/dotfile/04-window-management/macos-window-tools/) | Rectangle / Amethyst / AeroSpace / yabai 選型判讀與配置範例                              |
| [Linux Tiling WM 生態](/linux/dotfile/04-window-management/linux-tiling-wm/)    | 主流 tiling WM 比較（i3/sway/Hyprland/bspwm/dwm）、多螢幕處理、dotfile 中的角色          |
| [Wayland 顯示協議](/linux/dotfile/04-window-management/wayland-explainer/)      | Wayland 架構、跟 X11 的差異、XWayland 相容層、2026 採用現況、為什麼 tiling WM 選 Wayland |

macOS 讀者的主線是前兩篇（浮動 vs 平鋪、macOS 工具鏈）。Linux Tiling WM 生態和 Wayland 顯示協議是想在 VM 或實機上體驗 Linux 桌面的選讀——macOS 上用 AeroSpace 或 yabai 的讀者可以直接跳到[同步與 Bootstrap](/linux/dotfile/08-sync-bootstrap/)。

## 跨分類引用

- → [模組五：Hyprland 配置](/linux/dotfile/05-hyprland-config/)：Hyprland 的完整配置實務
- → [模組六：桌面 Rice 設計](/linux/dotfile/06-rice-design/)：compositor 之上的狀態列、啟動器、通知、配色系統
- → [模組一：管理工具與目錄結構](/linux/dotfile/01-dotfile-management/)：WM 配置怎麼進 dotfile repo
- → [模組八：同步、Bootstrap 與環境重建](/linux/dotfile/08-sync-bootstrap/)：跨機器搬移時硬體相關設定怎麼處理
