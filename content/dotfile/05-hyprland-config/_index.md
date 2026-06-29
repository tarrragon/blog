---
title: "模組五：Hyprland 配置"
date: 2026-06-29
description: "要在 Linux 上設定 Hyprland 平鋪式桌面時回來讀 — 配置檔結構、keybind 設計、monitor/workspace 設定、常見 plugin"
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

Hyprland 是 Wayland 上的動態平鋪式 compositor，在 tiling WM 裡少見地重視視覺效果——流暢的視窗動畫、圓角、模糊、漸層邊框。這個模組教它的配置檔怎麼寫、核心概念是什麼、以及常見的設定場景。

模組四講了平鋪式視窗管理的概念和選型，這裡直接進入 Hyprland 的配置實務。之後的 VM 實測專案會用這些配置做實際安裝和驗證。

## 配置檔位置與結構

Hyprland 的主配置檔在 `~/.config/hypr/hyprland.conf`。修改後即時生效（不需要重新登入或重啟），這是它的一個明確優點。

配置檔支援 `source` 指令拆分模組：

```bash
# ~/.config/hypr/hyprland.conf — 主入口

source = ~/.config/hypr/monitors.conf
source = ~/.config/hypr/keybinds.conf
source = ~/.config/hypr/rules.conf
source = ~/.config/hypr/autostart.conf
source = ~/.config/hypr/appearance.conf
```

拆分的理由跟 shell 配置模組化相同——職責分離、改一類設定不用在一千行裡找位置。

## Monitor 設定

monitor 設定是硬體相關的核心配置，每台機器都不同。

```bash
# ~/.config/hypr/monitors.conf

# 語法：monitor = name, resolution@refreshrate, position, scale
monitor = DP-1, 2560x1440@144, 0x0, 1
monitor = HDMI-A-1, 1920x1080@60, 2560x0, 1

# 筆電內建螢幕
monitor = eDP-1, preferred, auto, 1.5

# 預設規則（未明確列出的螢幕）
monitor = , preferred, auto, 1
```

`position` 決定多螢幕的空間排列——`0x0` 是左上角原點，`2560x0` 表示在第一個螢幕的右邊。`scale` 處理 HiDPI 顯示（1.5 表示 150% 縮放）。

查詢可用的 monitor 名稱：`hyprctl monitors`

這個檔案是典型的「機器專屬設定」。如果用 chezmoi，可以用 template 依機器名稱切換；如果用 stow，可以把 monitors.conf 排除在 Git 外、每台機器手動寫。

## Keybind 設計

Keybind 是平鋪式 WM 的操作核心。Hyprland 用 `bind` 指令定義：

```bash
# ~/.config/hypr/keybinds.conf

# 變數定義（讓後面更易讀）
$mod = SUPER

# 基本操作
bind = $mod, Return, exec, alacritty          # 開 terminal
bind = $mod, Q, killactive                     # 關閉當前視窗
bind = $mod, D, exec, wofi --show drun        # 啟動器
bind = $mod, F, fullscreen, 0                  # 全螢幕切換
bind = $mod SHIFT, Space, togglefloating       # 切換浮動/平鋪

# 焦點移動（vim 風格）
bind = $mod, H, movefocus, l
bind = $mod, J, movefocus, d
bind = $mod, K, movefocus, u
bind = $mod, L, movefocus, r

# 視窗移動
bind = $mod SHIFT, H, movewindow, l
bind = $mod SHIFT, J, movewindow, d
bind = $mod SHIFT, K, movewindow, u
bind = $mod SHIFT, L, movewindow, r

# 視窗大小調整
binde = $mod CTRL, H, resizeactive, -20 0
binde = $mod CTRL, J, resizeactive, 0 20
binde = $mod CTRL, K, resizeactive, 0 -20
binde = $mod CTRL, L, resizeactive, 20 0

# Workspace 切換（1-9）
bind = $mod, 1, workspace, 1
bind = $mod, 2, workspace, 2
bind = $mod, 3, workspace, 3
bind = $mod, 4, workspace, 4
bind = $mod, 5, workspace, 5
bind = $mod, 6, workspace, 6
bind = $mod, 7, workspace, 7
bind = $mod, 8, workspace, 8
bind = $mod, 9, workspace, 9

# 把視窗送到指定 workspace
bind = $mod SHIFT, 1, movetoworkspace, 1
bind = $mod SHIFT, 2, movetoworkspace, 2
bind = $mod SHIFT, 3, movetoworkspace, 3
# ... 以此類推

# 螢幕截圖
bind = , Print, exec, grimblast copy area      # 選區截圖到剪貼簿
bind = $mod, Print, exec, grimblast copy output # 整個螢幕截圖

# 多螢幕焦點切換
bind = $mod, comma, focusmonitor, l
bind = $mod, period, focusmonitor, r

# 把視窗丟到另一個螢幕
bind = $mod SHIFT, comma, movewindow, mon:l
bind = $mod SHIFT, period, movewindow, mon:r
```

`bind` 和 `binde` 的差異：`binde` 允許長按重複觸發（用在 resize 這種需要連續操作的場景）。

Keybind 設計原則：

- **$mod** 用 SUPER（Windows/Command 鍵）避免跟應用程式快捷鍵衝突
- **方向操作**統一用 vim 的 HJKL，降低記憶負擔
- **modifier 分層**：$mod 是焦點、$mod+SHIFT 是移動、$mod+CTRL 是調整大小
- 常用操作（開 terminal、關視窗、切 workspace）放在最順手的位置

## Workspace 設定

Workspace 是平鋪式桌面的空間管理單位。Hyprland 的 workspace 是動態的——不需要預先定義多少個，按了不存在的 workspace 編號就會自動建立。

```bash
# 把特定 workspace 綁定到特定螢幕
workspace = 1, monitor:DP-1, default:true
workspace = 2, monitor:DP-1
workspace = 3, monitor:DP-1
workspace = 7, monitor:HDMI-A-1, default:true
workspace = 8, monitor:HDMI-A-1
workspace = 9, monitor:HDMI-A-1
```

常見的使用模式：

- Workspace 1-3 放在主螢幕（寫程式用）
- Workspace 7-9 放在副螢幕（瀏覽器、通訊軟體、監控）
- 用鍵盤瞬間切換（$mod + 數字鍵），比 alt-tab 在一堆視窗裡找快

## Window Rules

Window rules 讓特定應用程式在開啟時自動套用設定——指定 workspace、強制浮動、設定大小等：

```bash
# ~/.config/hypr/rules.conf

# 特定 app 自動送到指定 workspace
windowrulev2 = workspace 8, class:^(firefox)$
windowrulev2 = workspace 9, class:^(Slack)$

# 設定面板、對話框等維持浮動（不進平鋪）
windowrulev2 = float, class:^(pavucontrol)$
windowrulev2 = float, title:^(Open File)$
windowrulev2 = float, title:^(Save As)$

# Picture-in-picture 浮動 + 置頂 + 固定大小
windowrulev2 = float, title:^(Picture-in-Picture)$
windowrulev2 = pin, title:^(Picture-in-Picture)$
windowrulev2 = size 480 270, title:^(Picture-in-Picture)$
```

查詢應用程式的 class 和 title：`hyprctl clients`

Window rules 是讓平鋪式桌面「不只是把所有東西硬塞格子」的關鍵——識別哪些 app 適合浮動、哪些適合指定位置，需要累積使用經驗。

## 外觀設定

```bash
# ~/.config/hypr/appearance.conf

general {
    gaps_in = 5
    gaps_out = 10
    border_size = 2
    col.active_border = rgba(89b4faee) rgba(cba6f7ee) 45deg
    col.inactive_border = rgba(313244aa)
    layout = dwindle       # 分割演算法：dwindle 或 master
}

decoration {
    rounding = 8           # 圓角半徑
    blur {
        enabled = true
        size = 5
        passes = 2
    }
    shadow {
        enabled = true
        range = 15
        render_power = 3
    }
}

animations {
    enabled = true

    bezier = ease, 0.25, 0.1, 0.25, 1

    animation = windows, 1, 4, ease, slide
    animation = windowsOut, 1, 4, ease, slide
    animation = fade, 1, 3, ease
    animation = workspaces, 1, 4, ease, slide
}
```

Dwindle vs Master layout：

- **Dwindle**：每個新視窗把當前區域一分為二（螺旋式切分），適合不固定視窗數量的工作流
- **Master**：一個主區域 + 其餘視窗堆疊在側邊，適合「一個主力視窗 + 多個參考視窗」的模式

## Autostart

```bash
# ~/.config/hypr/autostart.conf

# 桌面元件
exec-once = waybar                          # 狀態列
exec-once = mako                            # 通知
exec-once = hyprpaper                       # 桌布

# 系統服務
exec-once = /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1
exec-once = wl-paste --type text --watch cliphist store   # 剪貼簿歷史
```

`exec-once` 只在 Hyprland 啟動時跑一次（不會在 config reload 時重複執行）。跟 `exec`（每次 reload 都跑）區分。

## 常見 Plugin

Hyprland 有 plugin 系統，用 `hyprpm`（Hyprland Plugin Manager）管理：

- **hyprexpo**：workspace overview（鳥瞰所有 workspace 的縮圖）
- **hyprspace**：類似 macOS Mission Control 的 workspace 切換動畫
- **hy3**：i3/sway 風格的手動 tiling layout（dwindle 的替代方案）

Plugin 的配置也放在 hyprland.conf 裡，是 dotfile 的一部分。

## Dotfile 結構對應

```text
~/dotfiles/
└── hyprland/
    └── .config/
        └── hypr/
            ├── hyprland.conf      # 主入口（只有 source 行）
            ├── monitors.conf      # 硬體相關、可能排除或 template
            ├── keybinds.conf
            ├── rules.conf
            ├── autostart.conf
            └── appearance.conf
```

## 穩定性與維護的務實面

Hyprland 的開發節奏快、功能更新激進。配置檔的語法和可用選項會隨版本變動——某次系統更新後，原本正常的配置項可能被改名或移除。

應對策略：

- 更新前先看 [Hyprland wiki 的 Configuring 頁面](https://wiki.hyprland.org/Configuring/) 和 changelog
- dotfile repo 的 commit message 記錄「因應 Hyprland vX.Y 改了什麼設定」
- 如果用 Arch 的 rolling release，`pacman -Syu` 前先確認 Hyprland 是否有 breaking change（Arch 社群通常會在論壇預警）

這是模組四提過的代價——把日常桌面建立在高速移動的專案上，持續的配置維護是實際成本。
