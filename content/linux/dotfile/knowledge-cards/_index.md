---
title: "Linux 術語卡"
date: 2026-06-29
description: "dotfile 管理、平鋪式視窗管理、桌面客製化、安裝與除錯相關的術語索引"
weight: 99
tags: ["dotfile", "linux", "knowledge-cards"]
---

Linux 系列（dotfile / 安裝 / 除錯 / 工具）共用的關鍵術語。各卡片會在對應章節深入說明、這裡提供快速查閱入口，install / debug / tools 各篇的術語首現處也會連回這裡。

術語卡會隨教材擴展逐步補充。

## 語言與工具

| 卡片                                                                   | 主題                                                         |
| ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| [Lua 腳本語言](/linux/dotfile/knowledge-cards/lua-scripting-language/) | Hyprland / Neovim 配置檔使用的腳本語言，配置檔需要的最小知識 |
| [GNU Stow](/linux/dotfile/knowledge-cards/gnu-stow/)                   | symlink farm manager，dotfile 管理的核心工具之一             |
| [AUR（Arch User Repository）](/linux/dotfile/knowledge-cards/aur/)     | Arch 社群自建套件庫，paru/yay 為何用來裝官方 repo 沒有的套件 |
| [Quickshell](/linux/dotfile/knowledge-cards/quickshell/)               | Qt6/QML 的桌面 shell runtime，Caelestia 的執行引擎           |

## 系統概念

| 卡片                                                                                                | 主題                                                               |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [TTY](/linux/dotfile/knowledge-cards/tty/)                                                          | Linux 核心的純文字終端機介面，桌面故障時的救生通道                 |
| [initramfs](/linux/dotfile/knowledge-cards/initramfs/)                                              | 開機初期掛真 root 之前的臨時根檔系統，ESP 大小要算進它             |
| [UEFI 開機鏈](/linux/dotfile/knowledge-cards/uefi-boot-chain/)                                      | 韌體到 kernel 的交棒過程，bootloader 選型與開機故障的依據          |
| [分區識別（PARTUUID / FSUUID）](/linux/dotfile/knowledge-cards/partition-identification/)           | 分區的穩定識別方式，fstab / bootloader 怎麼指涉分區                |
| [字型的可用集合在 process 啟動時決定](/linux/dotfile/knowledge-cards/font-availability-at-startup/) | 裝了字型但畫面還是豆腐時的判讀依據                                 |
| [Session Lock](/linux/dotfile/knowledge-cards/session-lock/)                                        | 鎖屏是 compositor 持有的安全狀態，殺 process 不等於解鎖            |
| [Compositor（合成器）](/linux/dotfile/knowledge-cards/compositor/)                                  | Wayland 下把畫面合成與視窗管理合一的核心程式，多個系統狀態的持有者 |
| [fontconfig](/linux/dotfile/knowledge-cards/fontconfig/)                                            | 字型搜尋、匹配與 fallback 的底層服務，fc-* 工具分工                |
| [logind Session 與 Seat](/linux/dotfile/knowledge-cards/logind-session-seat/)                       | 誰持有 VT 與輸入權，SSH 起不了桌面與 loginctl 假象的根因           |

## 文化與術語

| 卡片                                                           | 主題                                           |
| -------------------------------------------------------------- | ---------------------------------------------- |
| [Rice（桌面視覺客製化）](/linux/dotfile/knowledge-cards/rice/) | Linux 桌面社群的視覺客製化文化，詞源和涵蓋範圍 |
