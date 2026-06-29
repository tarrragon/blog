---
title: "Linux Tiling WM 生態"
date: 2026-06-29
description: "要在 Linux 上選 tiling WM（i3/sway/Hyprland/bspwm）或理解 Wayland vs X11 差異時回來讀"
weight: 3
tags: ["dotfile", "linux", "window-manager", "tiling", "hyprland", "wayland"]
---

Linux 桌面的視窗管理跑在**顯示協議（display protocol）**上，目前有兩套。

**X11**（X Window System）是用了三十多年的傳統協議。成熟、穩定、所有工具都支援。設計上的根本問題是安全性——任何 X11 應用程式都能讀取其他視窗的內容和鍵盤輸入，這是協議層的限制，不是 bug。

**Wayland** 是設計來取代 X11 的新協議。每個應用程式只看得到自己的視窗、效能更好、對現代硬體的支援更完整。多數主流發行版已經把 Wayland 設為預設，但部分老舊應用程式和特殊需求（某些螢幕錄製、遠端桌面工具）的支援還在追趕中，這些情境會透過 XWayland（相容層）跑 X11 應用程式。

新的 tiling WM 主要基於 Wayland 開發，X11 上的老牌（i3, bspwm, dwm）仍然活躍但不再是未來方向。

## 主流 Tiling WM

**i3（X11）/ sway（Wayland）** 是社群最大、文件最齊全、行為最可預測的選擇。i3 跑在 X11 上，sway 是它的 Wayland 移植，配置格式幾乎相同。配置檔用自己的語法，直覺的 `key = action` 對應。

```text
# sway/config 片段
set $mod Mod4
bindsym $mod+h focus left
bindsym $mod+j focus down
bindsym $mod+k focus up
bindsym $mod+l focus right
bindsym $mod+Shift+h move left
bindsym $mod+1 workspace number 1
bindsym $mod+2 workspace number 2
```

穩定性是 i3/sway 最大的賣點——配置寫好之後很少因為更新而壞掉。適合想要可靠的平鋪工作流、不需要華麗視覺效果的人。

**Hyprland（Wayland）** 吸引的是在意桌面視覺品質的平鋪使用者——看 r/unixporn 的 Hyprland 截圖就知道，流暢的視窗切換動畫、圓角、視窗模糊、漸層邊框，這些傳統 tiling WM 社群視為不必要的裝飾，Hyprland 做成內建功能並且認真打磨。配置檔改完即時生效（hot reload），迭代調教的回饋循環很短。

這份視覺投入換來的 trade-off 是穩定性。開發節奏快意味著偶爾會有 breaking changes——某次更新後配置語法改了（2026 年 4 月的 Lua 遷移就是一例）、某個選項改名或移除。把它當主力桌面，要有「更新後可能要回來調配置」的心理準備。[Hyprland 配置](/dotfile/05-hyprland-config/)會詳細講它的設定。

**bspwm（X11）** 是純粹的 BSP 樹狀分割。它只做一件事：管理視窗的樹狀結構。所有操作透過 `bspc` 命令列工具驅動，快捷鍵綁定交給 sxhkd（一個獨立的快捷鍵 daemon）。UNIX 哲學——每個工具只做一件事，組合起來用。

**dwm（X11）** 極簡到配置要改 C 原始碼然後重新編譯。不是給「想要方便配置」的人用的，而是給「想要完全理解自己桌面每一行程式碼」的人用的。

## 拼裝式桌面的代價

Linux tiling WM 的桌面是你自己拼出來的：compositor（Hyprland/sway）負責視窗管理、狀態列（waybar）負責頂部資訊條、啟動器（rofi/wofi）負責 app 搜尋啟動、通知（mako/dunst）負責通知彈窗、鎖屏另外裝。每一塊是不同專案、不同作者。

好處是每一塊都可以換。壞處是當某件事壞了，你要自己判斷是哪一層的問題。藍牙選單不能點？可能是狀態列的 module 設定錯、可能是 blueman 沒跑、可能是 D-Bus session 有問題。完整桌面環境（KDE/GNOME）幫你整合測試過了，拼裝式桌面沒有這層保障。

## 多螢幕的處理

多螢幕是自動平鋪比較能展現價值的場景。每個螢幕是獨立的平鋪區域，視窗在哪個螢幕就在那個螢幕的範圍內平鋪。

快捷鍵跨螢幕操作是標配功能：把焦點跳到另一個螢幕、把當前視窗丟到另一個螢幕（丟過去後自動融入那邊的平鋪佈局）。三螢幕時這個便利性比單螢幕更明顯——純滑鼠拖視窗跨螢幕需要的移動距離很長。

工作區跟螢幕的綁定方式是各工具差異最大的地方。

macOS 的 Spaces 是綁定螢幕的——每個螢幕有自己獨立的一組 Spaces。yabai 沿用這個行為，切換工作區時只影響當前螢幕。AeroSpace 用自己的虛擬工作區繞過 macOS 原生 Spaces 的限制，多螢幕操作被普遍認為更穩定、更直覺。

Hyprland 的 workspace 可以動態指派到不同螢幕——workspace 3 現在在螢幕 A，你可以把它移到螢幕 B。這種模型彈性最大，但也需要清楚的心智模型來管理「哪個 workspace 在哪」。

熱插拔螢幕（接上、拔掉外接螢幕）是各工具的常見痛點。拔掉螢幕時，該螢幕上的視窗要搬到剩餘螢幕重新平鋪；插上螢幕時，佈局要擴展。多數工具有對應設定（記住螢幕配置、自動還原佈局），但體驗不見得完美，偶爾需要手動整理。

## Dotfile 中的視窗管理配置

視窗管理是 dotfile 管理裡「桌面層」的核心。WM 配置檔決定了整個桌面的操作邏輯——快捷鍵怎麼綁、視窗間距多大、哪些 app 要浮動、工作區怎麼分配。

macOS 工具的配置檔通常是一個檔案：AeroSpace 的 `~/.aerospace.toml`、yabai 的 `~/.yabairc` + `~/.skhdrc`、Amethyst 的 `~/.amethyst.yml`。把這些檔案放進 dotfile repo，換 Mac 時就能還原整套視窗管理行為。

Linux tiling WM 的配置在 `~/.config/` 下，通常是一個資料夾：Hyprland 的 `~/.config/hypr/`、sway 的 `~/.config/sway/`、i3 的 `~/.config/i3/`。除了 WM 本身，狀態列（waybar 的 `~/.config/waybar/`）、啟動器（rofi 的 `~/.config/rofi/`）、通知（mako 的 `~/.config/mako/`）等周邊元件的配置也各自有檔案。一套完整的 Linux 平鋪桌面，dotfile repo 裡可能會有十幾個配置目錄——這也是為什麼 Linux 桌面客製化社群那麼依賴 dotfile 管理工具（見[管理工具與目錄結構](/dotfile/01-dotfile-management/)）。

跟螢幕硬體綁定的設定（螢幕解析度、縮放比、螢幕排列順序）通常也寫在 WM 配置裡。這部分在跨機器搬移 dotfile 時需要調整——同一份 Hyprland 配置裡的 `monitor` 設定，在筆電上是一個螢幕、在桌機上可能是三個。常見做法是把硬體相關設定拆到單獨檔案（如 `monitors.lua`），主配置用 `require` 引入，這樣跨機器時只需要替換這一個檔案。[同步與環境重建](/dotfile/07-sync-bootstrap/)會講跨機器搬移時怎麼處理這類硬體差異。
