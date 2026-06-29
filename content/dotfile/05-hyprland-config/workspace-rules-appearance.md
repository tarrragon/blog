---
title: "Workspace、Window Rules 與外觀"
date: 2026-06-29
description: "Hyprland 的 workspace 綁定螢幕、window rules 設定浮動例外、外觀動畫調教、autostart 和 plugin 管理時回來讀"
weight: 2
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

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

### Dwindle vs Master layout

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

- 更新前先看 Hyprland wiki 的 Configuring 頁面和 changelog
- dotfile repo 的 commit message 記錄「因應 Hyprland vX.Y 改了什麼設定」
- 如果用 Arch 的 rolling release，`pacman -Syu` 前先確認 Hyprland 是否有 breaking change（Arch 社群通常會在論壇預警）

這是[模組四](/dotfile/04-window-management/)提過的代價——把日常桌面建立在高速移動的專案上，持續的配置維護是實際成本。
