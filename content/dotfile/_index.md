---
title: "Dotfile 工作環境配置指南"
date: 2026-06-29
description: "個人開發環境的配置管理 — dotfile 結構設計、同步策略、shell 與終端機配置、平鋪式視窗管理、桌面客製化，從個人工具鏈延伸到團隊環境標準化"
weight: 40
tags: ["dotfile", "linux", "workflow"]
---

開發者的工作環境是一組配置檔的集合：shell 怎麼設定、編輯器用什麼快捷鍵、終端機長什麼樣、視窗怎麼排列。這些配置檔在 Unix 系統上以 `.` 開頭（隱藏檔），統稱 dotfile。

dotfile 管理解決的核心問題是**環境可重現性**。一台新機器、一次重灌、一個 VM，都應該能用一份 Git repo 還原成你熟悉的工作環境。不做管理的代價是：每次換機器都在重新手動設定，每次都少記一兩個東西，每次都花一兩天才回到順手的狀態。

## 和其他系列的關係

| 系列                       | 聚焦                                          | 和 Dotfile 的交集                                                               |
| -------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------- |
| [Infra](/infra/)           | 雲端基礎設施地基（IaC、網路、身分、環境分離） | Infra 是組織的環境 as code，Dotfile 是個人的環境 as code，思想平行              |
| [DevOps](/devops/)         | 服務營運（負載、擴展、容量、成本）            | DevOps 工程師的日常工具鏈（多終端機、SSH、log tail）正是 dotfile 高度客製的場景 |
| [CLI](/cli/)               | TUI 工具、多工器、檔案管理器                  | CLI 工具的配置檔是 dotfile 管理的核心對象                                       |
| [Monitoring](/monitoring/) | 客戶端監控體系                                | Monitoring 有獨立的 hands-on 專案做實測，Dotfile 也會有 VM 實測專案             |

Infra 教「組織的地基怎麼用 code 管理」，Dotfile 教「個人的工作桌面怎麼用 code 管理」。模組八把兩者接起來——當個人 dotfile 的思想擴展到團隊，就是 devcontainer 和標準化開發環境。

## 教學模組

模組編號反映學習路徑：先理解為什麼、再學怎麼管理、然後逐層處理 shell/終端機/視窗管理/視覺客製化，最後談同步可攜性和團隊化。模組四到六是 Linux 桌面環境的深度實作，之後會搭配 VM 專案做 hands-on 實測。

| 模組                                                              | 主題                                                 | 回答什麼問題                              |
| ----------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------- |
| [模組零：Dotfile 心智模型](/dotfile/00-dotfile-mindset/)          | 什麼是 dotfile、為什麼要管理、環境可重現性           | 為什麼不能每次手動設定就好                |
| [模組一：管理工具與目錄結構](/dotfile/01-dotfile-management/)     | bare repo / stow / chezmoi、目錄設計、版控工作流     | dotfile 怎麼用 Git 管、目錄該怎麼組織     |
| [模組二：Shell 配置](/dotfile/02-shell-config/)                   | zsh/bash 結構化配置、模組化拆分、alias/function/PATH | .zshrc 該怎麼寫才不會長成一坨             |
| [模組三：終端機與編輯器](/dotfile/03-terminal-ecosystem/)         | terminal emulator 選型、tmux/zellij、neovim 基礎     | 終端機生態的配置檔有哪些、怎麼管理        |
| [模組四：視窗管理與自動平鋪](/dotfile/04-window-management/)      | 手動 vs 自動平鋪、macOS 工具鏈、Linux tiling WM      | Rectangle 不夠用的時候該換什麼            |
| [模組五：Hyprland 配置](/dotfile/05-hyprland-config/)             | Hyprland 安裝、核心設定、keybind、monitor、workspace | Hyprland 的配置檔怎麼寫、核心概念是什麼   |
| [模組六：桌面 Rice 設計](/dotfile/06-rice-design/)                | 狀態列、啟動器、通知、配色系統、desktop shell        | 桌面怎麼從「能用」變成「好看又好用」      |
| [模組七：同步、Bootstrap 與環境重建](/dotfile/07-sync-bootstrap/) | 跨機器同步、install script、secret 排除、VM 對比     | 換機器時怎麼一鍵還原、哪些東西不該進 repo |
| [模組八：從個人到團隊](/dotfile/08-team-environment/)             | devcontainer、nix、商業開發環境標準化                | 個人 dotfile 的思想怎麼延伸到團隊環境管理 |

## VM 實測專案

模組四到六的 Linux 桌面配置會搭配一個獨立的 VM 專案做 hands-on 實測（類似 [Monitoring](/monitoring/) 系列搭配 monitor 專案的關係）。教材負責概念與配置邏輯的說明，VM 專案負責實際安裝、調教、截圖驗證。VM 專案會在教材完成後另外建立。
