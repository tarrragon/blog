---
title: "模組六：桌面 Rice 設計"
date: 2026-06-29
description: "Hyprland 桌面從能用到好看好用 — 狀態列、啟動器、通知、鎖屏、配色系統的設計與配置"
weight: 6
tags: ["dotfile", "rice", "waybar", "hyprland", "linux"]
---

Rice 在 Linux 桌面社群指的是桌面視覺客製化——把系統外觀調教成個人化的美學呈現。這個詞源自汽車改裝文化（Race Inspired Cosmetic Enhancements 的逆向縮寫），在 Linux 圈已轉為中性的圈內用語，r/unixporn 社群就是圍繞這件事運轉的。

[Hyprland 配置](/dotfile/05-hyprland-config/)教了 compositor（Wayland 下負責視窗排列和畫面合成的程式）本身的設定。這個模組處理的是 compositor 之上的「桌面 shell」層——狀態列、啟動器、通知、鎖屏、桌布、配色系統。做法有兩條路：自己從 Waybar + Wofi + Mako 等獨立工具一個個拼裝，或用 Caelestia 這類預組裝的桌面 shell 一次部署。

## 章節文章

| 文章                                                                                       | 主題                                                                         |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| [桌面 Shell 元件：狀態列、啟動器與通知](/dotfile/06-rice-design/desktop-shell-components/) | 拼裝式桌面的元件組成、Waybar 狀態列配置、Wofi/Rofi 啟動器、Mako 通知         |
| [配色系統、鎖屏與 GTK 主題](/dotfile/06-rice-design/color-system-theming/)                 | Hyprlock 鎖屏配置、配色變數集中管理、GTK/Qt 主題統一、投資報酬判讀           |
| [Caelestia 總覽](/dotfile/06-rice-design/caelestia-overview/)                              | Quickshell 框架、提供的元件、跟手動拼裝和 AGS/Eww 的 trade-off、定位認知     |
| [Caelestia 安裝](/dotfile/06-rice-design/caelestia-installation/)                          | AUR 套件、CLI 安裝流程、依賴清單、登入管理器、CLI 指令、VM 測試範圍          |
| [Caelestia 配置](/dotfile/06-rice-design/caelestia-configuration/)                         | shell.json 結構、token 系統、hypr-user.lua、動態取色、已知問題、dotfile 結構 |

## 跨分類引用

- → [模組三：終端機與編輯器](/dotfile/03-terminal-ecosystem/)：Nerd Font 安裝是 Waybar icon 正常顯示的前提
- → [模組五：Hyprland 配置](/dotfile/05-hyprland-config/)：compositor 的 appearance 設定（圓角、動畫）跟 rice 的視覺層互補
- → [模組一：管理工具與目錄結構](/dotfile/01-dotfile-management/)：各 rice 元件的配置檔怎麼放進 stow 結構
- → [Session Lock](/dotfile/knowledge-cards/session-lock/)：鎖屏的安全模型——殺 process 不等於解鎖
- → [字型的可用集合在 process 啟動時決定](/dotfile/knowledge-cards/font-availability-at-startup/)：裝了字型但狀態列 / 通知還是豆腐時的判讀
- → [fontconfig](/dotfile/knowledge-cards/fontconfig/)：字型搜尋、匹配與 fallback 機制
