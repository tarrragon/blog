---
title: "Workspace、Window Rules 與外觀"
date: 2026-06-29
description: "Hyprland 的 workspace 綁定螢幕、window rules 設定浮動例外、外觀動畫調教、layout 選型、autostart 和 plugin 管理時回來讀"
weight: 2
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

## Workspace 設定

Workspace 是平鋪式桌面的空間管理單位。Hyprland 的 workspace 是動態的——不需要預先定義多少個，按了不存在的 workspace 編號就會自動建立。

```lua
-- 把特定 workspace 綁定到特定螢幕
hl.config({
    workspace = {
        "1, monitor:DP-1, default:true",
        "2, monitor:DP-1",
        "3, monitor:DP-1",
        "7, monitor:HDMI-A-1, default:true",
        "8, monitor:HDMI-A-1",
        "9, monitor:HDMI-A-1",
    },
})
```

常見的使用模式：

- Workspace 1-3 放在主螢幕（寫程式用）
- Workspace 7-9 放在副螢幕（瀏覽器、通訊軟體、監控）
- 用鍵盤瞬間切換（SUPER + 數字鍵），比 alt-tab 在一堆視窗裡找快

### Per-workspace layout 覆寫

```lua
hl.config({
    workspace = {
        "1, layoutopt:orientation:left",     -- workspace 1 用左側 master
        "2, layoutopt:orientation:top",      -- workspace 2 用頂部 master
    },
})
```

> **[VM 可測試]** Workspace 切換、綁定邏輯、per-workspace layout。  
> **[需實機測試]** Workspace 綁定到特定實體螢幕的行為。

## Window Rules

Window rules 讓特定應用程式在開啟時自動套用設定——指定 workspace、強制浮動、設定大小等。

```lua
hl.config({
    windowrule = {
        -- 特定 app 自動送到指定 workspace
        "workspace 8, class:^(firefox)$",
        "workspace 9, class:^(Slack)$",

        -- 設定面板、對話框等維持浮動（不進平鋪）
        "float, class:^(pavucontrol)$",
        "float, class:^(nm-connection-editor)$",
        "float, title:^(Open File)$",
        "float, title:^(Save As)$",

        -- Picture-in-picture 浮動 + 置頂 + 固定大小
        "float, title:^(Picture-in-Picture)$",
        "pin, title:^(Picture-in-Picture)$",
        "size 480 270, title:^(Picture-in-Picture)$",
        "move 100%-490 50, title:^(Picture-in-Picture)$",

        -- 視窗透明度（active inactive）
        "opacity 0.9, class:^(kitty)$",
        "opacity 0.85 0.75, class:^(Code)$",

        -- 防止 Electron app 自動最大化
        "suppressevent maximize, class:.*",

        -- XWayland video bridge（螢幕分享用）
        "opacity 0.0 override, class:^(xwaylandvideobridge)$",
        "noanim, class:^(xwaylandvideobridge)$",
        "noinitialfocus, class:^(xwaylandvideobridge)$",
        "maxsize 1 1, class:^(xwaylandvideobridge)$",
        "noblur, class:^(xwaylandvideobridge)$",
    },
})
```

### 查詢應用程式的 class 和 title

```bash
hyprctl clients          # 列出所有開啟的視窗（含 class、title、PID 等）
hyprctl activewindow     # 當前焦點視窗的資訊
```

Window rules 用 regex 匹配 `class` 和 `title`。靜態 rules 匹配的是視窗開啟時的初始值（`initialTitle` / `initialClass`）。

Window rules 是讓平鋪式桌面「不只是把所有東西硬塞格子」的關鍵——識別哪些 app 適合浮動、哪些適合指定位置，需要累積使用經驗。

> **[VM 可測試]** Window rules 邏輯、workspace 指派、float 規則。查 class/title 也在 VM 裡能做。

## Layout 配置

### Dwindle

每個新視窗把當前區域一分為二（螺旋式切分），適合不固定視窗數量的工作流：

```lua
hl.config({
    dwindle = {
        pseudotile = true,       -- 允許 app 請求 pseudo-tiling（保留原始大小）
        preserve_split = true,   -- 不自動改變分割方向
        force_split = 2,         -- 0=跟隨滑鼠, 1=永遠左/上, 2=永遠右/下
        smart_split = false,
        smart_resizing = true,
    },
})
```

### Master

一個主區域 + 其餘視窗堆疊在側邊，適合「一個主力視窗 + 多個參考視窗」的模式：

```lua
hl.config({
    master = {
        new_on_top = false,       -- 新視窗放 master 還是 stack
        orientation = "left",     -- master 區域位置：left / right / top / bottom / center
        mfact = 0.55,             -- master 區域佔螢幕的比例
    },
})
```

在 `general` 裡設定預設 layout：

```lua
hl.config({
    general = {
        layout = "dwindle",       -- 或 "master"
    },
})
```

> **[VM 可測試]** Layout 切換和參數調整的行為邏輯。

## 外觀設定

```lua
hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 10,
        border_size = 2,
        ["col.active_border"] = "rgba(89b4faee) rgba(cba6f7ee) 45deg",
        ["col.inactive_border"] = "rgba(313244aa)",
    },
    decoration = {
        rounding = 8,

        blur = {
            enabled = true,
            size = 5,             -- 模糊半徑（越高越模糊、越吃 GPU）
            passes = 2,           -- 模糊次數（越多越平滑、越重）
            vibrancy = 0.17,
            noise = 0.02,
            new_optimizations = true,
        },

        shadow = {
            enabled = true,
            range = 15,
            render_power = 3,     -- 1-4，衰減曲線
            color = "0xee1a1a2e",
        },

        dim_inactive = false,
        dim_strength = 0.2,

        active_opacity = 1.0,
        inactive_opacity = 0.95,
    },
})
```

> **[需實機測試]** blur 的效能影響和視覺品質——這是 Hyprland 最吃 GPU 的功能。VM 裡建議 `blur = { enabled = false }` 避免卡頓。shadow 和 rounding 在軟體渲染下可以動但會很慢。

## 動畫設定

```lua
-- 定義 bezier 曲線
hl.animation("bezier", "ease", 0.25, 0.1, 0.25, 1)
hl.animation("bezier", "overshot", 0.05, 0.9, 0.1, 1.05)

-- Spring 物理動畫（較新的替代方案）
hl.animation("spring", "bouncy", 1, 8, 0)   -- damping, frequency, speed

-- 套用動畫
hl.animation("animation", "windows", 1, 4, "ease", "slide")
hl.animation("animation", "windowsOut", 1, 4, "ease", "popin 80%")
hl.animation("animation", "fade", 1, 3, "ease")
hl.animation("animation", "workspaces", 1, 4, "ease", "slide")

-- 關閉特定動畫
hl.animation("animation", "windowsMove", 0)
```

VM 裡跑 Hyprland 時，建議完全關閉動畫以維持可用的操作速度：

```lua
hl.config({
    animations = {
        enabled = false,
    },
})
```

> **[需實機測試]** 動畫流暢度是 Hyprland 的核心賣點，只有實機能評估。VM 裡的卡頓是 GPU 加速不足造成的，不代表 Hyprland 本身的效能。

## Autostart

```lua
hl.config({
    exec_once = {
        -- 桌面元件
        "waybar",
        "mako",
        "hyprpaper",

        -- 系統服務
        "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1",
        "wl-paste --type text --watch cliphist store",

        -- Idle daemon（閒置鎖屏）
        "hypridle",
    },
})
```

`exec_once` 只在 Hyprland 啟動時跑一次（config reload 不會重複執行）。如果需要每次 reload 都重跑某個指令，用 `exec`（但多數情況不需要）。

## Plugin 系統

Hyprland 用 `hyprpm`（Hyprland Plugin Manager）管理 plugin：

```bash
hyprpm update                                              # 更新 plugin index
hyprpm add https://github.com/hyprwm/hyprland-plugins     # 加入官方 plugin repo
hyprpm enable hyprexpo                                     # 啟用 plugin
hyprpm disable hyprexpo                                    # 停用 plugin
hyprpm list                                                # 列出可用 plugin
```

| Plugin         | 功能                                             |
| -------------- | ------------------------------------------------ |
| **hyprexpo**   | workspace 鳥瞰（所有 workspace 縮圖一覽）        |
| **hy3**        | i3/sway 風格的手動 tiling layout（替代 dwindle） |
| **hyprspace**  | 類似 macOS Mission Control 的 workspace 切換動畫 |
| **hyprbars**   | 視窗標題列（可自訂按鈕）                         |
| **hyprtrails** | 游標拖尾特效                                     |

Plugin 的配置寫在 hyprland.lua 裡，是 dotfile 的一部分。

> **[VM 可測試]** 不依賴 GPU 的 plugin（hy3、hyprbars）。  
> **[需實機測試]** 視覺特效類 plugin（hyprexpo、hyprspace、hyprtrails）。

## Dotfile 結構對應

```text
~/dotfiles/
└── hyprland/
    └── .config/
        └── hypr/
            ├── hyprland.lua       # 主入口（只有 require 行）
            ├── monitors.lua       # 硬體相關、可能排除或 template
            ├── keybinds.lua
            ├── rules.lua
            ├── autostart.lua
            ├── appearance.lua
            └── env.lua
```

## 穩定性與維護的務實面

Hyprland 的開發節奏快、功能更新激進。v0.55 的 Lua 遷移就是一個典型案例——配置格式整個換掉，舊的 `.conf` 只會再支援一到兩個版本。配置檔的語法和可用選項會隨版本變動。

應對策略：

- 更新前先看 Hyprland wiki 的 Configuring 頁面和 changelog
- dotfile repo 的 commit message 記錄「因應 Hyprland vX.Y 改了什麼設定」
- 如果用 Arch 的 rolling release，`pacman -Syu` 前先確認 Hyprland 是否有 breaking change（Arch 社群通常會在論壇預警）
- 官方提供遷移工具（如 `hyprlang2lua`），格式變更時優先使用

這是[模組四](/dotfile/04-window-management/)提過的代價——把日常桌面建立在高速移動的專案上，持續的配置維護是實際成本。

## VM 與實機測試對照

| 項目              | VM 可測試 | 需實機測試 |
| ----------------- | --------- | ---------- |
| 配置語法 / 結構   | 可        |            |
| Keybind 設計      | 可        |            |
| Window rules 邏輯 | 可        |            |
| Workspace 切換    | 可        |            |
| Layout 參數       | 可        |            |
| Autostart 順序    | 可        |            |
| Plugin 配置       | 部分      | 視覺類     |
| 動畫流暢度        |           | 必要       |
| Blur 效能 / 品質  |           | 必要       |
| 多螢幕排列        |           | 必要       |
| HiDPI 縮放        |           | 必要       |
| 觸控板 / 手勢     |           | 必要       |
| 媒體鍵 / 亮度鍵   |           | 必要       |
| NVIDIA 驅動設定   |           | 必要       |
| 螢幕分享          |           | 必要       |
| 休眠 / 喚醒       |           | 必要       |
| 合蓋行為          |           | 必要       |
