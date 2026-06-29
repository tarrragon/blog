---
title: "macOS 視窗管理工具鏈"
date: 2026-06-29
description: "macOS 上想用鍵盤管理視窗、不確定該用哪個工具時回來讀"
weight: 2
tags: ["dotfile", "macos", "window-manager", "aerospace", "yabai"]
---

macOS 的視窗系統由 WindowServer 控制，第三方工具能做的主要是「排列邏輯」——決定視窗的位置和大小。視覺效果（動畫、模糊、圓角）由系統控制，第三方工具改不了。這是跟 Linux tiling WM 最大的差異。

## macOS 原生 Window Tiling（macOS 15+）

macOS Sequoia（15，2024 年 9 月）內建了 window tiling 功能：鍵盤快捷鍵把視窗貼到螢幕的半邊或四分之一、拖拉到邊緣自動貼齊（edge snap）、相鄰視窗可以組成 tile group 一起調整比例。

原生 tiling 的邊界：沒有多工作區管理、快捷鍵自訂空間有限（只能用系統偏好設定裡的固定選項）、不支援自動平鋪（仍然是手動觸發的 snap，不會在開新視窗時自動重排）。

如果「貼到半邊 + 邊緣吸附」就足夠，原生功能免安裝即可使用。以下第三方工具解決的是原生功能做不到的事：更多排列選項（Rectangle）、自動平鋪（Amethyst）、完整的鍵盤工作流加多工作區（AeroSpace / yabai）。

## Rectangle

免費、開源。用快捷鍵把視窗貼到螢幕的半邊、三分之一、角落。不是自動平鋪——每個視窗都要你主動下指令。安裝後開箱即用，學習成本最低。

適合的情境：只需要快速排版、不想花時間學新操作邏輯、偶爾分割就滿足需求。

配置檔位置：`~/Library/Preferences/com.knollsoft.Rectangle.plist`（macOS plist 格式，不太適合手動編輯，通常用 GUI 設定）。

## Amethyst

自動平鋪，安裝後視窗就會自動排列。提供多種 layout（tall, wide, fullscreen, column 等）可以用快捷鍵切換。設定比 Rectangle 多但比 yabai 少，是「想要自動平鋪但不想深度折騰」的選擇。

配置檔：`~/.amethyst.yml`，YAML 格式，可以版控。

## AeroSpace

近年最受歡迎的選擇。核心優勢是**不需要關閉 SIP**（System Integrity Protection）——它用自己實作的虛擬工作區概念，不依賴 macOS 原生的 Spaces，因此繞過了很多系統層的限制。

配置是純文字的 TOML 檔 `~/.aerospace.toml`，改完即時生效。工作區模型靈活，多螢幕支援被普遍認為比 yabai 穩定。

```toml
# ~/.aerospace.toml 片段
after-startup-command = ['workspace 1']

[gaps]
inner.horizontal = 10
inner.vertical = 10
outer.left = 10
outer.right = 10

[mode.main.binding]
alt-h = 'focus left'
alt-j = 'focus down'
alt-k = 'focus up'
alt-l = 'focus right'
alt-shift-h = 'move left'
alt-shift-j = 'move down'
alt-shift-k = 'move up'
alt-shift-l = 'move right'
alt-1 = 'workspace 1'
alt-2 = 'workspace 2'
alt-3 = 'workspace 3'
```

配置結構直覺：gaps 控制視窗間距、binding 定義快捷鍵對應的動作。整份檔案進 dotfile repo 就能跨機器還原操作習慣。

## yabai + skhd

功能最完整的 macOS tiling WM。yabai 負責視窗管理，skhd 負責快捷鍵綁定。支援 BSP（binary space partitioning）樹狀分割——每次開新視窗都是把現有空間二分，形成一棵樹，你可以操作樹的節點來旋轉、交換、調整比例。

代價是部分進階功能（某些視窗操作、取消動畫）需要部分關閉 SIP。對某些人這是門檻，對另一些人不是問題。

配置檔是 shell script：`.yabairc`（yabai 設定）和 `.skhdrc`（快捷鍵設定），進 dotfile repo 管理。

```bash
# .yabairc 片段
yabai -m config layout bsp
yabai -m config window_gap 10
yabai -m config top_padding 10
yabai -m config bottom_padding 10

# 某些 app 不適合平鋪，設為浮動
yabai -m rule --add app="System Preferences" manage=off
yabai -m rule --add app="Calculator" manage=off
yabai -m rule --add app="Finder" title="Info" manage=off
```

## 選型判讀

選工具的判準不是「哪個最強」，而是「你願意花多少時間、想要多少控制權」。

只需要快速排視窗、不想改工作習慣，Rectangle 足夠。想要自動平鋪但學習曲線要短，Amethyst 是進入點。想要完整的平鋪工作流、多工作區管理、純文字配置、又不想動系統安全設定，AeroSpace 是目前多數人推薦的首選。想要最大的控制權、願意處理 SIP 和更複雜的配置，yabai 給你最多彈性。

從 Rectangle 跳到 AeroSpace 或 yabai 是一次操作思維的轉換——從「我指定每個視窗去哪」變成「我操作版面結構、WM 負責排列」。這個轉換需要一兩週的適應期，適應期內效率會暫時下降。
