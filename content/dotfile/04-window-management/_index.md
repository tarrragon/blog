---
title: "模組四：視窗管理與自動平鋪"
date: 2026-06-29
description: "同時開多個視窗時的排列策略 — 手動貼齊跟自動平鋪的差距在哪、macOS 和 Linux 各有哪些工具、多螢幕怎麼處理、什麼情境值得從浮動切換到平鋪"
tags: ["dotfile", "window-manager", "tiling", "hyprland", "workflow"]
---

視窗管理器（window manager, WM）負責決定螢幕上的視窗怎麼排列、怎麼切換、怎麼調整大小。每個桌面環境都有一個 WM，差別在於它是讓你用滑鼠自己拖，還是按規則自動幫你排好。

## 浮動式與平鋪式

桌面視窗管理分成兩種基本模式。

**浮動式（floating）** 是多數人熟悉的模式。視窗可以重疊、可以任意拖拉調整大小、可以最小化藏起來。macOS、Windows、GNOME、KDE 預設都是浮動式。操作直覺是「每個視窗是一張紙，自己決定放哪裡」。

**平鋪式（tiling）** 的規則不同：視窗自動排列填滿螢幕、不重疊，由 WM 的規則決定版面怎麼切割。開一個新視窗時，WM 自動把現有空間分一半給它；關掉一個視窗時，相鄰視窗自動擴展填補。操作直覺是「螢幕是一塊蛋糕，WM 負責切」。

多數平鋪式 WM 支援**混合模式**：特定視窗可以設為浮動，脫離平鋪規則。設定面板、密碼輸入框、小工具這類不適合塞進格子的視窗，通常會設成浮動例外。平鋪是預設，浮動是按需啟用的例外。

## 手動貼齊 vs 自動平鋪

在進入平鋪式 WM 之前，macOS 和 Windows 都提供了「手動貼齊」功能——用快捷鍵或拖拉把視窗貼到螢幕的半邊、角落、三分之一。macOS 原生的 window snapping、Windows 的 Snap Layout、以及 Rectangle 和 Magnet 這類第三方工具都屬於這個範疇。

手動貼齊跟自動平鋪的差距，在視窗數量少的時候幾乎感覺不到。開兩個視窗、左右各半，手動按一下快捷鍵就到位，完全夠用。

差距在視窗數量多的時候才出現。

同時開五、六個視窗（多個終端機、編輯器、瀏覽器、文件、log 輸出）的情境下，手動貼齊會變成持續的「俄羅斯方塊」——每開一個新視窗要想它該放哪、按對應的快捷鍵；關掉一個視窗就留下空洞，要手動拖拉其他視窗去填。注意力不斷被版面管理打斷。

自動平鋪在這個情境下的優勢有三層。

第一層是**自動回填**。開視窗、關視窗，WM 自動重新分配空間，版面永遠是滿的、整齊的。你不用做任何版面決策。

第二層是**操作對象的轉換**。手動貼齊的操作對象是「某個視窗」——把 A 視窗貼到左邊、把 B 視窗貼到右上。平鋪式 WM 的操作對象是「版面結構」——把焦點往右移、把當前視窗跟隔壁交換、把這一格再水平切一半。你操作的是位置關係，不是絕對座標。

第三層是**工作區整合**。平鋪式工作流通常搭配多個工作區（workspace），每個工作區是一套獨立的平鋪佈局。「編輯器和終端機在工作區 1、瀏覽器在工作區 2、通訊軟體在工作區 4」——用快捷鍵瞬間切換整套上下文，而不是在一堆重疊視窗裡找。手動貼齊工具通常不帶工作區管理。

## macOS 上的視窗管理工具鏈

macOS 的視窗系統由 WindowServer 控制，第三方工具能做的主要是「排列邏輯」——決定視窗的位置和大小。視覺效果（動畫、模糊、圓角）由系統控制，第三方工具改不了。這是跟 Linux tiling WM 最大的差異。

### Rectangle

免費、開源。用快捷鍵把視窗貼到螢幕的半邊、三分之一、角落。不是自動平鋪——每個視窗都要你主動下指令。安裝後開箱即用，學習成本最低。

適合的情境：只需要快速排版、不想花時間學新操作邏輯、偶爾分割就滿足需求。

配置檔位置：`~/Library/Preferences/com.knollsoft.Rectangle.plist`（macOS plist 格式，不太適合手動編輯，通常用 GUI 設定）。

### Amethyst

自動平鋪，安裝後視窗就會自動排列。提供多種 layout（tall, wide, fullscreen, column 等）可以用快捷鍵切換。設定比 Rectangle 多但比 yabai 少，是「想要自動平鋪但不想深度折騰」的選擇。

配置檔：`~/.amethyst.yml`，YAML 格式，可以版控。

### AeroSpace

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

### yabai + skhd

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

### 選型判讀

選工具的判準不是「哪個最強」，而是「你願意花多少時間、想要多少控制權」。

只需要快速排視窗、不想改工作習慣，Rectangle 足夠。想要自動平鋪但學習曲線要短，Amethyst 是進入點。想要完整的平鋪工作流、多工作區管理、純文字配置、又不想動系統安全設定，AeroSpace 是目前多數人推薦的首選。想要最大的控制權、願意處理 SIP 和更複雜的配置，yabai 給你最多彈性。

從 Rectangle 跳到 AeroSpace 或 yabai 是一次操作思維的轉換——從「我指定每個視窗去哪」變成「我操作版面結構、WM 負責排列」。這個轉換需要一兩週的適應期，適應期內效率會暫時下降。

## Linux 上的 Tiling WM 生態

Linux 桌面的視窗管理跑在**顯示協議（display protocol）**上，目前有兩套。

**X11**（X Window System）是用了三十多年的傳統協議。成熟、穩定、所有工具都支援。設計上的根本問題是安全性——任何 X11 應用程式都能讀取其他視窗的內容和鍵盤輸入，這是協議層的限制，不是 bug。

**Wayland** 是設計來取代 X11 的新協議。每個應用程式只看得到自己的視窗、效能更好、對現代硬體的支援更完整。多數主流發行版已經把 Wayland 設為預設，但部分老舊應用程式和特殊需求（某些螢幕錄製、遠端桌面工具）的支援還在追趕中，這些情境會透過 XWayland（相容層）跑 X11 應用程式。

新的 tiling WM 主要基於 Wayland 開發，X11 上的老牌（i3, bspwm, dwm）仍然活躍但不再是未來方向。

### 主流 Tiling WM

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

**Hyprland（Wayland）** 在 tiling WM 裡少見地重視視覺效果。流暢的視窗切換動畫、圓角、視窗模糊、漸層邊框——這些在傳統 tiling WM 社群裡通常被視為不必要的花俏，Hyprland 把它們做成內建功能。配置檔改完即時生效（hot reload），開發節奏快、功能迭代快。

代價是穩定性不如 i3/sway。開發活躍意味著偶爾會有 breaking changes——某次更新後配置語法改了、某個選項改名或移除。你的桌面建立在一個高速移動的專案上，要有「更新後可能要調配置」的心理準備。[模組五](/dotfile/05-hyprland-config/)會詳細講它的配置。

**bspwm（X11）** 是純粹的 BSP 樹狀分割。它只做一件事：管理視窗的樹狀結構。所有操作透過 `bspc` 命令列工具驅動，快捷鍵綁定交給 sxhkd（一個獨立的快捷鍵 daemon）。UNIX 哲學——每個工具只做一件事，組合起來用。

**dwm（X11）** 極簡到配置要改 C 原始碼然後重新編譯。不是給「想要方便配置」的人用的，而是給「想要完全理解自己桌面每一行程式碼」的人用的。

### 拼裝式桌面的代價

Linux tiling WM 的桌面是你自己拼出來的：compositor（Hyprland/sway）負責視窗管理、狀態列（waybar）負責頂部資訊條、啟動器（rofi/wofi）負責 app 搜尋啟動、通知（mako/dunst）負責通知彈窗、鎖屏另外裝。每一塊是不同專案、不同作者。

好處是每一塊都可以換。壞處是當某件事壞了，你要自己判斷是哪一層的問題。藍牙選單不能點？可能是狀態列的 module 設定錯、可能是 blueman 沒跑、可能是 D-Bus session 有問題。完整桌面環境（KDE/GNOME）幫你整合測試過了，拼裝式桌面沒有這層保障。

## 多螢幕的處理

多螢幕是自動平鋪比較能展現價值的場景。每個螢幕是獨立的平鋪區域，視窗在哪個螢幕就在那個螢幕的範圍內平鋪。

快捷鍵跨螢幕操作是標配功能：把焦點跳到另一個螢幕、把當前視窗丟到另一個螢幕（丟過去後自動融入那邊的平鋪佈局）。三螢幕時這個便利性比單螢幕更明顯——純滑鼠拖視窗跨螢幕需要的移動距離很長。

工作區跟螢幕的綁定方式是各工具差異最大的地方。

macOS 的 Spaces 是綁定螢幕的——每個螢幕有自己獨立的一組 Spaces。yabai 沿用這個行為，切換工作區時只影響當前螢幕。AeroSpace 用自己的虛擬工作區繞過 macOS 原生 Spaces 的限制，多螢幕操作被普遍認為更穩定、更直覺。

Hyprland 的 workspace 可以動態指派到不同螢幕——workspace 3 現在在螢幕 A，你可以把它移到螢幕 B。這種模型彈性最大，但也需要清楚的心智模型來管理「哪個 workspace 在哪」。

熱插拔螢幕（接上、拔掉外接螢幕）是各工具的常見痛點。拔掉螢幕時，該螢幕上的視窗要搬到剩餘螢幕重新平鋪；插上螢幕時，佈局要擴展。多數工具有對應設定（記住螢幕配置、自動還原佈局），但體驗不見得完美，偶爾需要手動整理。

## 適用判讀

平鋪式視窗管理的投資報酬率取決於你的工作型態。

**高回報情境**：經常同時操作五個以上視窗、多數是「方方正正、可平鋪」的 app（終端機、編輯器、瀏覽器、文件閱讀器）、鍵盤操作為主、多螢幕、工作需要頻繁切換上下文（多個專案、不同任務區）。

**低回報情境**：大量使用需要特定比例或自由拖拉的 app（設計工具、影片剪輯、簡報製作）、很少同時開多個視窗、已經習慣且滿意目前的工作流、不想花時間學新鍵位。

**折衷方案**：所有平鋪式工具都支援 per-app 的浮動例外。不適合平鋪的 app（設定面板、計算機、某些對話框）設成浮動，其餘維持平鋪。這不是全有全無的選擇。

一個常見的踩坑模式是：看到 Hyprland 的截圖很漂亮，衝動裝了，發現日常有一半 app 不適合平鋪、鍵位記不住、每次更新都要修配置，兩週後放棄。務實的進入路徑是先在目前的系統上試手動貼齊工具（macOS 的 Rectangle 或 AeroSpace），確認自己真的享受鍵盤操作視窗的節奏，再往 Linux tiling WM 推進。或者用 VM 跑 Hyprland 體驗看看——體驗打折（VM 沒有 GPU 加速，動畫會卡），但能確認自己是否喜歡這種操作邏輯，再決定要不要花時間在實體機上搭建。

## Dotfile 中的視窗管理配置

視窗管理是 dotfile 管理裡「桌面層」的核心。WM 配置檔決定了整個桌面的操作邏輯——快捷鍵怎麼綁、視窗間距多大、哪些 app 要浮動、工作區怎麼分配。

macOS 工具的配置檔通常是一個檔案：AeroSpace 的 `~/.aerospace.toml`、yabai 的 `~/.yabairc` + `~/.skhdrc`、Amethyst 的 `~/.amethyst.yml`。把這些檔案放進 dotfile repo，換 Mac 時就能還原整套視窗管理行為。

Linux tiling WM 的配置在 `~/.config/` 下，通常是一個資料夾：Hyprland 的 `~/.config/hypr/`、sway 的 `~/.config/sway/`、i3 的 `~/.config/i3/`。除了 WM 本身，狀態列（waybar 的 `~/.config/waybar/`）、啟動器（rofi 的 `~/.config/rofi/`）、通知（mako 的 `~/.config/mako/`）等周邊元件的配置也各自有檔案。一套完整的 Linux 平鋪桌面，dotfile repo 裡可能會有十幾個配置目錄——這也是為什麼 Linux 桌面客製化社群那麼依賴 dotfile 管理工具（[模組一](/dotfile/01-dotfile-management/)）。

跟螢幕硬體綁定的設定（螢幕解析度、縮放比、螢幕排列順序）通常也寫在 WM 配置裡。這部分在跨機器搬移 dotfile 時需要調整——同一份 `hyprland.conf` 裡的 `monitor` 設定，在筆電上是一個螢幕、在桌機上可能是三個。常見做法是把硬體相關設定拆到單獨檔案（如 `monitors.conf`），主配置用 `source` 引入，這樣跨機器時只需要替換這一個檔案。[模組七](/dotfile/07-sync-bootstrap/)會講跨機器同步時怎麼處理這類硬體差異。
