---
title: "Dotfile 術語卡"
date: 2026-06-29
description: "dotfile 管理、平鋪式視窗管理、桌面客製化相關的術語索引"
weight: 99
tags: ["dotfile", "knowledge-cards"]
---

本系列使用的關鍵術語。各卡片會在對應章節深入說明、這裡提供快速查閱入口。

術語卡會隨教材擴展逐步補充。

## 語言與工具

| 卡片                                                             | 主題                                                         |
| ---------------------------------------------------------------- | ------------------------------------------------------------ |
| [Lua 腳本語言](/dotfile/knowledge-cards/lua-scripting-language/) | Hyprland / Neovim 配置檔使用的腳本語言，配置檔需要的最小知識 |
| [GNU Stow](/dotfile/knowledge-cards/gnu-stow/)                   | symlink farm manager，dotfile 管理的核心工具之一             |

## 系統概念

| 卡片                                                                                | 主題                                                      |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [TTY](/dotfile/knowledge-cards/tty/)                                                | Linux 核心的純文字終端機介面，桌面故障時的救生通道        |
| [initramfs](/dotfile/knowledge-cards/initramfs/)                                    | 開機初期掛真 root 之前的臨時根檔系統，ESP 大小要算進它    |
| [UEFI 開機鏈](/dotfile/knowledge-cards/uefi-boot-chain/)                            | 韌體到 kernel 的交棒過程，bootloader 選型與開機故障的依據 |
| [分區識別（PARTUUID / FSUUID）](/dotfile/knowledge-cards/partition-identification/) | 分區的穩定識別方式，fstab / bootloader 怎麼指涉分區       |

## 文化與術語

| 卡片                                                     | 主題                                           |
| -------------------------------------------------------- | ---------------------------------------------- |
| [Rice（桌面視覺客製化）](/dotfile/knowledge-cards/rice/) | Linux 桌面社群的視覺客製化文化，詞源和涵蓋範圍 |
