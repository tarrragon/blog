---
title: "模組六：桌面 Rice 設計"
date: 2026-06-29
description: "Hyprland 桌面從能用到好看好用 — 狀態列、啟動器、通知、鎖屏、配色系統的設計與配置"
weight: 6
tags: ["dotfile", "rice", "waybar", "hyprland", "linux"]
---

Rice 在 Linux 桌面社群指的是桌面視覺客製化——把系統外觀調教成個人化的美學呈現。這個詞源自汽車改裝文化（Race Inspired Cosmetic Enhancements 的逆向縮寫），在 Linux 圈已轉為中性的圈內用語，r/unixporn 社群就是圍繞這件事運轉的。

[模組五](/dotfile/05-hyprland-config/)教了 Hyprland compositor 本身的配置（平鋪邏輯、keybind、workspace）。這個模組處理的是 compositor 之上的「桌面 shell」層——狀態列、啟動器、通知、鎖屏、桌布、配色系統。這些元件各自是獨立的小工具，用配置檔組合成一套協調的桌面體驗。

## 章節文章

| 文章                                                                                       | 主題                                                                 |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| [桌面 Shell 元件：狀態列、啟動器與通知](/dotfile/06-rice-design/desktop-shell-components/) | 拼裝式桌面的元件組成、Waybar 狀態列配置、Wofi/Rofi 啟動器、Mako 通知 |
| [配色系統、鎖屏與 GTK 主題](/dotfile/06-rice-design/color-system-theming/)                 | Hyprlock 鎖屏配置、配色變數集中管理、GTK/Qt 主題統一、投資報酬判讀   |

## 跨分類引用

- → [模組三：終端機與編輯器](/dotfile/03-terminal-ecosystem/)：Nerd Font 安裝是 Waybar icon 正常顯示的前提
- → [模組五：Hyprland 配置](/dotfile/05-hyprland-config/)：compositor 的 appearance 設定（圓角、動畫）跟 rice 的視覺層互補
- → [模組一：管理工具與目錄結構](/dotfile/01-dotfile-management/)：各 rice 元件的配置檔怎麼放進 stow 結構
