---
title: "模組八：同步、Bootstrap 與環境重建"
date: 2026-06-29
description: "換機器或重灌時怎麼還原工作環境 — bootstrap script 設計、套件清單管理、跨機器同步策略、secret 排除，以及 VM 快照和 dotfile 重建兩種思路的場景判讀"
weight: 8
tags: ["dotfile", "bootstrap", "sync"]
---

環境重建是 dotfile 管理的最終目的：拿到一台空白機器，能在可預期的時間內還原成你熟悉的工作環境。這件事有兩條根本不同的路線——「拍照」（VM 快照）和「重建指令」（dotfile + install script），選哪條決定了你之後所有的管理策略。

## 章節文章

| 文章                                                                                            | 主題                                                                                                                          |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| [拍照 vs 重建指令：環境重建的兩種思路](/linux/dotfile/08-sync-bootstrap/snapshot-vs-rebuild/)   | VM 快照和 dotfile 重建的本質差異、各自的守備範圍與場景判讀                                                                    |
| [Bootstrap Script 與套件清單管理](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)  | install script 的冪等性設計、OS 分流、Brewfile / packages.txt 套件清單管理                                                    |
| [跨機器同步、Secret 管理與環境重建流程](/linux/dotfile/08-sync-bootstrap/sync-strategy-secret/) | Git push/pull vs 自動同步、secret 三層級管理、從空白機器到完整工作環境的 end-to-end（範例用 Arch + Hyprland，macOS 同樣適用） |

## 跨分類引用

- → [模組一：管理工具與目錄結構](/linux/dotfile/01-dotfile-management/)：stow / chezmoi 選型與跨平台三層模型
- → [模組五：Hyprland 配置](/linux/dotfile/05-hyprland-config/)：環境重建流程裡 monitor 設定的硬體相關調整
- → [模組九：從個人到團隊](/linux/dotfile/09-team-environment/)：個人 bootstrap 的思想怎麼延伸到團隊 onboarding
