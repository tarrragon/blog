---
title: "模組五：Hyprland 配置"
date: 2026-06-29
description: "要在 Linux 上設定 Hyprland 平鋪式桌面時回來讀"
weight: 5
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

Hyprland 是 Wayland 上的動態平鋪式 compositor，在 tiling WM 裡少見地重視視覺效果——流暢的視窗動畫、圓角、模糊、漸層邊框。這個模組教它的配置檔怎麼寫、核心概念是什麼、以及常見的設定場景。

[視窗管理與平鋪式工作流](/linux/dotfile/04-window-management/)講了平鋪概念和選型，這裡直接進入 Hyprland 的配置實務。之後的 VM 實測專案會用這些配置做實際安裝和驗證。

macOS 讀者如果不打算在 Linux 或 VM 上跑 Hyprland，可以跳到[同步、Bootstrap 與環境重建](/linux/dotfile/08-sync-bootstrap/)——bootstrap script 和 secret 管理的概念對 macOS 同樣適用。

## 章節文章

| 文章                                                                                            | 主題                                                                                                          |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [安裝與環境建置](/linux/dotfile/05-hyprland-config/hyprland-installation/)                      | Arch Linux 套件、GPU 驅動（AMD/Intel/NVIDIA 含完整設定）、配套工具、登入管理器、首次啟動除錯                  |
| [Hyprland 核心配置](/linux/dotfile/05-hyprland-config/hyprland-core-config/)                    | 配置檔位置與模組化拆分、monitor 設定、keybind 設計（含完整配置範例）                                          |
| [Workspace、Window Rules 與外觀](/linux/dotfile/05-hyprland-config/workspace-rules-appearance/) | workspace 設定、window rules、外觀設定、兩種平鋪分割演算法（dwindle / master）、autostart、plugin、穩定性維護 |
| [VM 環境設定與測試矩陣](/linux/dotfile/05-hyprland-config/hyprland-vm-setup/)                   | UTM/QEMU 設定、VM 環境變數、效能預期、VM 可測試 vs 需實機測試的完整矩陣                                       |

## 跨分類引用

- → [模組四：視窗管理與自動平鋪](/linux/dotfile/04-window-management/)：平鋪式 WM 的概念和選型
- → [模組六：桌面 Rice 設計](/linux/dotfile/06-rice-design/)：compositor 之上的狀態列、啟動器、通知、配色系統
- → [模組七：桌面環境維護與故障排除](/linux/dotfile/07-desktop-maintenance/)：Hyprland crash、GPU hang、config 寫錯時的診斷和恢復
- → [模組八：同步、Bootstrap 與環境重建](/linux/dotfile/08-sync-bootstrap/)：跨機器搬移時硬體相關設定怎麼處理
- → [Linux 工具選單：圖形桌面工具](/linux/tools/gui/)：在 Hyprland 下加圖形檔案管理員（Thunar / Nemo / PCManFM-Qt）的相依取捨
