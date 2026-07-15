---
title: "模組零：Dotfile 心智模型"
date: 2026-06-29
description: "換機器、開 VM、重灌系統時需要快速還原開發環境，或想釐清哪些配置該版控、哪些該排除時回來讀"
weight: 0
tags: ["dotfile", "workflow"]
---

Dotfile 管理的核心能力是**環境可重現性**：把個人開發環境的配置狀態變成版控下的代碼，讓任何一台空白機器都能用一份 Git repo 還原成你熟悉的工作桌面。

Unix 系統用檔名開頭的 `.` 標記隱藏檔。shell 配置（`.bashrc`、`.zshrc`）、Git 設定（`.gitconfig`）、SSH 設定（`.ssh/config`）、以及 `~/.config/` 底下各種工具的配置目錄，都屬於這個範疇。「dotfile 管理」指的是把這些散落在家目錄各處的配置檔集中到一個 Git repo，建立版本歷史、可以跨機器同步、可以在新環境一鍵部署。

## 章節文章

| 文章                                                                                            | 主題                                                                                   |
| ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [環境可重現性與配置分類](/linux/dotfile/00-dotfile-mindset/environment-reproducibility/)        | 為什麼要管理 dotfile、哪些東西該進 repo、核心層 / 工具層 / 桌面層的分類判讀            |
| [Dotfile 跟 Infra IaC 的平行關係](/linux/dotfile/00-dotfile-mindset/dotfile-iac-parallel/)      | 兩者共用的原則與差異、「重建指令不是備份」的心智模型                                   |
| [環境建置的操作順序](/linux/dotfile/00-dotfile-mindset/setup-order-guide/)                      | 第一次建環境時先做什麼後做什麼——依賴順序路線圖，每步附對應模組連結                     |
| [乾淨機器驗證：宣告 vs 實際依賴](/linux/dotfile/00-dotfile-mindset/clean-machine-verification/) | 為什麼「可重現」要在乾淨機器實跑才驗得出——非-repo 狀態如何掩蓋缺口、原機是被污染的儀器 |

## 跨分類引用

- → [模組一：管理工具與目錄結構](/linux/dotfile/01-dotfile-management/)：怎麼把散落的配置檔收進 Git repo
- → [模組八：同步、Bootstrap 與環境重建](/linux/dotfile/08-sync-bootstrap/)：環境重建的完整流程
- → [模組九：從個人到團隊](/linux/dotfile/09-team-environment/)：dotfile 思想往團隊環境延伸
- → [Infra 基礎設施建置指南](/infra/)：組織層級的環境 as code
