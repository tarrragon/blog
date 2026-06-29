---
title: "模組五：Hyprland 配置"
date: 2026-06-29
description: "要在 Linux 上設定 Hyprland 平鋪式桌面時回來讀 — 配置檔結構、keybind 設計、monitor/workspace 設定、常見 plugin"
weight: 5
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

Hyprland 是 Wayland 上的動態平鋪式 compositor，在 tiling WM 裡少見地重視視覺效果——流暢的視窗動畫、圓角、模糊、漸層邊框。這個模組教它的配置檔怎麼寫、核心概念是什麼、以及常見的設定場景。

模組四講了平鋪式視窗管理的概念和選型，這裡直接進入 Hyprland 的配置實務。之後的 VM 實測專案會用這些配置做實際安裝和驗證。

## 章節文章

| 文章                                                                                      | 主題                                                                                       |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [Hyprland 核心配置](/dotfile/05-hyprland-config/hyprland-core-config/)                    | 配置檔位置與模組化拆分、monitor 設定、keybind 設計（含完整配置範例）                       |
| [Workspace、Window Rules 與外觀](/dotfile/05-hyprland-config/workspace-rules-appearance/) | workspace 設定、window rules、外觀設定（dwindle vs master）、autostart、plugin、穩定性維護 |

## 跨分類引用

- → [模組四：視窗管理與自動平鋪](/dotfile/04-window-management/)：平鋪式 WM 的概念和選型
- → [模組六：桌面 Rice 設計](/dotfile/06-rice-design/)：compositor 之上的狀態列、啟動器、通知、配色系統
- → [模組七：同步、Bootstrap 與環境重建](/dotfile/07-sync-bootstrap/)：跨機器搬移時硬體相關設定怎麼處理
