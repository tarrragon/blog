---
title: "Hyprland 核心配置"
date: 2026-06-29
description: "Hyprland 的配置檔該怎麼組織、monitor 怎麼設定、keybind 怎麼設計、輸入裝置和環境變數怎麼配時回來讀"
weight: 2
tags: ["dotfile", "hyprland", "wayland", "linux"]
---

Hyprland v0.55+ 使用 Lua 作為配置語言。Lua 語法基礎見 [Lua 腳本語言](/dotfile/knowledge-cards/lua-scripting-language/)。

## 配置檔位置與格式

Hyprland v0.55 起，配置格式從 hyprlang（`.conf`）遷移到 **Lua**（`.lua`）。主配置檔是 `~/.config/hypr/hyprland.lua`。如果 `.lua` 不存在但 `.conf` 存在，Hyprland 會回退讀取舊格式，但 hyprlang 已標記為棄用，後續版本會移除支援。

修改後即時生效（不需要重新登入或重啟）。第一次啟動時如果沒有配置檔，Hyprland 會自動產生範例配置。即使配置有語法錯誤，緊急快捷鍵（SUPER+Q 開 terminal、SUPER+M 離開）仍然可用。

> **[VM 可測試]** 配置檔格式和載入行為在 VM 裡跟實機完全相同。

### 模組化拆分

用 Lua 原生的 `require()` 拆分配置：

```lua
-- ~/.config/hypr/hyprland.lua — 主入口

require("monitors")      -- 載入 monitors.lua
require("keybinds")      -- 載入 keybinds.lua
require("rules")         -- 載入 rules.lua
require("autostart")     -- 載入 autostart.lua
require("appearance")    -- 載入 appearance.lua
require("env")           -- 載入 env.lua
```

`require("monitors")` 會從同目錄載入 `monitors.lua`。拆分的理由跟 shell 配置模組化相同——職責分離、改一類設定不用在一千行裡找位置。

### 從舊格式遷移

Hyprland 官方提供遷移工具：`hyprlang2lua`（Go，也有瀏覽器版）和 `hypr-migrate`。如果你是從零開始，直接用 Lua 格式。

## Monitor 設定

Monitor 設定是硬體相關的核心配置，每台機器都不同。

```lua
-- ~/.config/hypr/monitors.lua

hl.config({
    monitor = {
        -- 語法："name, resolution@refreshrate, position, scale"
        "DP-1, 2560x1440@144, 0x0, 1",
        "HDMI-A-1, 1920x1080@60, 2560x0, 1",

        -- 筆電內建螢幕
        "eDP-1, preferred, auto, 1.5",

        -- 預設規則（未明確列出的螢幕）
        ", preferred, auto, 1",

        -- 鏡像模式（DP-2 鏡像 DP-1 的畫面）
        -- "DP-2, preferred, auto, 1, mirror, DP-1",
    },
})
```

`position` 決定多螢幕的空間排列——`0x0` 是左上角原點，`2560x0` 表示在第一個螢幕的右邊。`scale` 處理 HiDPI 顯示（1.5 表示 150% 縮放）。

查詢可用的 monitor 名稱：`hyprctl monitors`

其他選項：

- `transform, 1` — 旋轉（0=正常、1=90 度、2=180 度、3=270 度）
- `vrr, 1` — 可變更新率（1=開啟、2=僅全螢幕）
- `bitdepth, 10` — 10-bit 色彩

### 筆電合蓋行為

```lua
-- 合蓋時關閉內建螢幕、開蓋時恢復
-- bindl = 即使輸入鎖定也能觸發（合蓋時需要）
hl.bindl("", "switch:on:Lid Switch", "exec", "hyprctl keyword monitor 'eDP-1, disable'")
hl.bindl("", "switch:off:Lid Switch", "exec", "hyprctl keyword monitor 'eDP-1, preferred, auto, 1'")
```

> **[需實機測試]** Monitor 位置排列、HiDPI 縮放、VRR、旋轉、多螢幕熱插拔、合蓋行為。VM 通常只有一個虛擬螢幕。

### Dotfile 管理策略

Monitor 設定是典型的「機器專屬」配置。如果用 chezmoi，可以用 template 依機器名稱切換；如果用 stow，可以把 `monitors.lua` 排除在 Git 外、每台機器手動寫。

## 輸入裝置配置

```lua
-- ~/.config/hypr/hyprland.lua 或拆到獨立檔案

hl.config({
    input = {
        kb_layout = "us",
        -- 多語系：kb_layout = "us,de",
        -- 切換：kb_options = "grp:alt_shift_toggle",
        -- Caps Lock 當 Escape：kb_options = "caps:escape",
        kb_options = "",

        follow_mouse = 1,         -- 焦點跟隨滑鼠
        sensitivity = 0,          -- -1.0 到 1.0（0 = 不修改）
        accel_profile = "flat",   -- flat 或 adaptive

        repeat_rate = 25,         -- 長按時每秒重複幾次
        repeat_delay = 600,       -- 按住多久開始重複（毫秒）

        touchpad = {
            natural_scroll = true,
            disable_while_typing = true,
            ["tap-to-click"] = true,
            drag_lock = false,
            scroll_factor = 1.0,
        },
    },
})
```

可用的 XKB options 查詢：`/usr/share/X11/xkb/rules/evdev.lst` 或 `localectl list-x11-keymap-options`。

> **[VM 可測試]** 鍵盤 layout、repeat rate。  
> **[需實機測試]** 觸控板設定、手勢、滑鼠靈敏度/加速曲線、多鍵盤配置。

## Keybind 設計

### Bind 類型

Hyprland 提供多種 bind 函式，處理不同互動模式：

| 函式          | 行為           | 適用場景                             |
| ------------- | -------------- | ------------------------------------ |
| `hl.bind()`   | 按一次觸發     | 多數快捷鍵                           |
| `hl.binde()`  | 長按連續觸發   | 調整視窗大小、音量                   |
| `hl.bindm()`  | 滑鼠綁定       | 拖曳移動 / 調整視窗                  |
| `hl.bindr()`  | 放開時觸發     | 切換模式                             |
| `hl.bindl()`  | 輸入鎖定也觸發 | 合蓋開關、鎖屏時的媒體鍵             |
| `hl.bindel()` | 連續 + 鎖定    | 鎖屏時的音量鍵（長按連續、鎖定可用） |

> **[VM 可測試]** 所有 keybind 邏輯和配置語法。

### 基本操作

```lua
-- ~/.config/hypr/keybinds.lua

-- 基本操作
hl.bind("SUPER", "Return", "exec", "kitty")
hl.bind("SUPER", "Q", "killactive")
hl.bind("SUPER", "D", "exec", "wofi --show drun")
hl.bind("SUPER", "F", "fullscreen", "0")
hl.bind("SUPER SHIFT", "Space", "togglefloating")

-- 焦點移動（vim 風格）
hl.bind("SUPER", "H", "movefocus", "l")
hl.bind("SUPER", "J", "movefocus", "d")
hl.bind("SUPER", "K", "movefocus", "u")
hl.bind("SUPER", "L", "movefocus", "r")

-- 視窗移動
hl.bind("SUPER SHIFT", "H", "movewindow", "l")
hl.bind("SUPER SHIFT", "J", "movewindow", "d")
hl.bind("SUPER SHIFT", "K", "movewindow", "u")
hl.bind("SUPER SHIFT", "L", "movewindow", "r")

-- 視窗大小調整（長按連續觸發）
hl.binde("SUPER CTRL", "H", "resizeactive", "-20 0")
hl.binde("SUPER CTRL", "J", "resizeactive", "0 20")
hl.binde("SUPER CTRL", "K", "resizeactive", "0 -20")
hl.binde("SUPER CTRL", "L", "resizeactive", "20 0")

-- 滑鼠綁定：SUPER + 左鍵拖曳移動、右鍵拖曳調整大小
hl.bindm("SUPER", "mouse:272", "movewindow")
hl.bindm("SUPER", "mouse:273", "resizewindow")

-- Workspace 切換
hl.bind("SUPER", "1", "workspace", "1")
hl.bind("SUPER", "2", "workspace", "2")
hl.bind("SUPER", "3", "workspace", "3")
hl.bind("SUPER", "4", "workspace", "4")
hl.bind("SUPER", "5", "workspace", "5")
hl.bind("SUPER", "6", "workspace", "6")
hl.bind("SUPER", "7", "workspace", "7")
hl.bind("SUPER", "8", "workspace", "8")
hl.bind("SUPER", "9", "workspace", "9")

-- 把視窗送到指定 workspace
hl.bind("SUPER SHIFT", "1", "movetoworkspace", "1")
hl.bind("SUPER SHIFT", "2", "movetoworkspace", "2")
hl.bind("SUPER SHIFT", "3", "movetoworkspace", "3")
-- 以此類推

-- 螢幕截圖
hl.bind("", "Print", "exec", "grimblast copy area")
hl.bind("SUPER", "Print", "exec", "grimblast copy output")

-- 多螢幕焦點切換
hl.bind("SUPER", "comma", "focusmonitor", "l")
hl.bind("SUPER", "period", "focusmonitor", "r")
hl.bind("SUPER SHIFT", "comma", "movewindow", "mon:l")
hl.bind("SUPER SHIFT", "period", "movewindow", "mon:r")
```

### 設計原則

- **SUPER**（Windows/Command 鍵）當 modifier，避免跟應用程式快捷鍵衝突
- **方向操作**統一用 vim 的 HJKL，降低記憶負擔
- **modifier 分層**：SUPER 是焦點、SUPER+SHIFT 是移動、SUPER+CTRL 是調整大小
- 常用操作（開 terminal、關視窗、切 workspace）放在最順手的位置

### Submap：模態快捷鍵

Submap 類似 vim 的模式切換——進入某個 submap 後，快捷鍵的意義改變，直到離開。適合需要連續操作的場景（如調整大小）：

```lua
-- 按 SUPER+R 進入 resize 模式
hl.bind("SUPER", "R", "submap", "resize")

-- 定義 resize 模式的快捷鍵
hl.submap("resize")
hl.binde("", "H", "resizeactive", "-20 0")
hl.binde("", "L", "resizeactive", "20 0")
hl.binde("", "K", "resizeactive", "0 -20")
hl.binde("", "J", "resizeactive", "0 20")
hl.bind("", "escape", "submap", "reset")   -- Escape 離開
hl.submap("reset")
```

進入 resize 模式後，直接按 HJKL（不需要 modifier）就能持續調整大小，按 Escape 回到正常模式。

### 媒體鍵與硬體鍵

```lua
-- 音量（鎖屏時也能用、長按連續觸發）
hl.bindel("", "XF86AudioRaiseVolume", "exec", "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+")
hl.bindel("", "XF86AudioLowerVolume", "exec", "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-")
hl.bindl("", "XF86AudioMute", "exec", "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")
hl.bindl("", "XF86AudioMicMute", "exec", "wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle")

-- 亮度
hl.bindel("", "XF86MonBrightnessUp", "exec", "brightnessctl s 10%+")
hl.bindel("", "XF86MonBrightnessDown", "exec", "brightnessctl s 10%-")

-- 媒體播放
hl.bindl("", "XF86AudioPlay", "exec", "playerctl play-pause")
hl.bindl("", "XF86AudioNext", "exec", "playerctl next")
hl.bindl("", "XF86AudioPrev", "exec", "playerctl previous")
```

> **[需實機測試]** 媒體鍵（XF86Audio*）、亮度鍵（XF86MonBrightness*）、合蓋開關——這些依賴實體硬體送出正確的 keycode。VM 鍵盤通常沒有這些鍵。

## 環境變數

環境變數在 `hl.config()` 的 `env` 區段設定，影響 Hyprland 自身和其下執行的應用程式：

```lua
-- ~/.config/hypr/env.lua

hl.config({
    env = {
        -- 游標主題
        "XCURSOR_SIZE, 24",
        "XCURSOR_THEME, Bibata-Modern-Classic",
        "HYPRCURSOR_SIZE, 24",
        "HYPRCURSOR_THEME, Bibata-Modern-Classic",

        -- Qt 應用程式
        "QT_AUTO_SCREEN_SCALE_FACTOR, 1",
        "QT_QPA_PLATFORM, wayland;xcb",
        "QT_QPA_PLATFORMTHEME, qt5ct",
        "QT_WAYLAND_DISABLE_WINDOWDECORATION, 1",

        -- GTK 應用程式
        "GDK_BACKEND, wayland,x11,*",

        -- XDG session
        "XDG_CURRENT_DESKTOP, Hyprland",
        "XDG_SESSION_TYPE, wayland",
        "XDG_SESSION_DESKTOP, Hyprland",

        -- Electron 應用程式（VS Code, Discord 等）
        "ELECTRON_OZONE_PLATFORM_HINT, auto",

        -- Firefox
        "MOZ_ENABLE_WAYLAND, 1",
    },
})
```

### NVIDIA 專用環境變數

如果使用 NVIDIA 顯卡，需要額外設定（AMD 和 Intel 不需要）：

```lua
-- 只在 NVIDIA 機器上加這些
hl.config({
    env = {
        "LIBVA_DRIVER_NAME, nvidia",
        "GBM_BACKEND, nvidia-drm",             -- Firefox 若崩潰就移除這行
        "__GLX_VENDOR_LIBRARY_NAME, nvidia",
        "NVD_BACKEND, direct",
    },
    cursor = {
        no_hardware_cursors = true,             -- NVIDIA 常見的游標問題修正
        allow_dumb_copy = true,
    },
})
```

> **[VM 不適用]** NVIDIA 環境變數和驅動設定在 VM 裡無意義——VM 使用 virtio-gpu 或軟體渲染。這些設定只在實體 NVIDIA 機器上測試。

### VM 專用環境變數

在 VM（UTM/QEMU）裡跑 Hyprland 需要額外的回退設定：

```lua
-- 只在 VM 裡加，實機要移除
hl.config({
    env = {
        "WLR_RENDERER_ALLOW_SOFTWARE, 1",
        "LIBGL_ALWAYS_SOFTWARE, 1",
        "WLR_NO_HARDWARE_CURSORS, 1",
    },
})
```

> **[待實測驗證]** Hyprland 0.40+ 遷移到 Aquamarine 渲染後端，`WLR_` 開頭的環境變數可能已失效。完整 VM 設定見 [VM 環境設定與測試矩陣](/dotfile/05-hyprland-config/hyprland-vm-setup/)。
