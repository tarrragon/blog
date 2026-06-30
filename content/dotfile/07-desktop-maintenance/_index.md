---
title: "模組七：桌面環境維護與故障排除"
date: 2026-06-30
description: "桌面凍結、compositor 掛了、或某個工具不回應時回來讀 — Linux 桌面的故障隔離模型、常見故障場景的恢復操作、日誌判讀與診斷工具"
weight: 7
tags: ["dotfile", "linux", "hyprland", "troubleshooting"]
---

模組零到六教的是怎麼建立桌面環境，這個模組教的是壞了怎麼修。

Linux 桌面環境跟 Windows 在故障模型上有根本的結構差異。Windows 的藍屏（BSOD）是核心層崩潰，整台機器停擺；Linux 桌面環境的大部分故障只影響 userspace，系統核心不受波及。理解這個隔離邊界，是判斷「當下該做什麼」的前提。

這個模組的閱讀方式跟其他模組不同。其他模組是線性學習——從頭讀到尾建立知識。這個模組是 reference——出問題時根據症狀查對應的恢復操作。第一篇建立概念模型，第二篇按場景查操作，第三篇教怎麼看日誌找根因。

## 章節文章

| 文章                                                                                | 主題                                                                              |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [Linux 桌面的故障隔離模型](/dotfile/07-desktop-maintenance/fault-isolation-model/)  | kernel vs userspace 隔離、compositor 掛了不等於系統崩潰、TTY                      |
| [常見故障場景與恢復操作](/dotfile/07-desktop-maintenance/common-failures-recovery/) | compositor crash、工具掛了、GPU hang、OOM、config 錯誤、suspend/resume 異常的處理 |
| [日誌判讀與診斷工具](/dotfile/07-desktop-maintenance/log-reading-diagnostic-tools/) | journalctl、dmesg、hyprctl、systemctl 的使用與常見 pattern                        |

## 跨分類引用

- -> [模組五：Hyprland 配置](/dotfile/05-hyprland-config/)：Hyprland 的配置結構和 hyprctl 指令
- -> [模組六：桌面 Rice 設計](/dotfile/06-rice-design/)：waybar / wofi / mako 等工具的配置位置
- -> [模組八：同步、Bootstrap 與環境重建](/dotfile/08-sync-bootstrap/)：環境損壞到無法修復時的重建策略
