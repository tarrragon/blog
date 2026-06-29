---
title: "Hyprland 核心配置"
date: 2026-06-29
description: "Hyprland 的配置檔該怎麼組織、monitor 怎麼設定、keybind 怎麼設計時回來讀"
weight: 1
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

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

### Keybind 設計原則

- **$mod** 用 SUPER（Windows/Command 鍵）避免跟應用程式快捷鍵衝突
- **方向操作**統一用 vim 的 HJKL，降低記憶負擔
- **modifier 分層**：$mod 是焦點、$mod+SHIFT 是移動、$mod+CTRL 是調整大小
- 常用操作（開 terminal、關視窗、切 workspace）放在最順手的位置
