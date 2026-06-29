---
title: "桌面 Shell 元件：狀態列、啟動器與通知"
date: 2026-06-29
description: "Hyprland 桌面要拼哪些元件、各元件的配置檔怎麼寫時回來讀"
weight: 1
tags: ["dotfile", "rice", "waybar", "wofi", "mako", "hyprland", "linux"]
---

完整桌面環境（GNOME、KDE）把這些元件整合在一起出貨。平鋪式 WM 的桌面是拼裝的——每個位置自己選工具：

| 功能     | 常見工具                     | 配置格式             |
| -------- | ---------------------------- | -------------------- |
| 狀態列   | Waybar, Eww, AGS             | JSON/JSONC, Yuck, JS |
| 啟動器   | Wofi, Rofi (wayland), Fuzzel | CSS + 設定檔         |
| 通知     | Mako, Dunst, SwayNC          | INI/TOML             |
| 鎖屏     | Hyprlock, Swaylock           | 自定義格式           |
| 桌布     | Hyprpaper, Swww, Mpvpaper    | 自定義格式           |
| 剪貼簿   | wl-clipboard + Cliphist      | CLI                  |
| 螢幕截圖 | Grimblast, Grim + Slurp      | CLI                  |

Caelestia 這類「desktop shell 專案」做的就是把上述元件統一設計、統一配色、統一出貨，省去自己一個個挑的功夫。它用的是 Quickshell（QML 框架）把所有元件包成一套風格一致的桌面。本模組教的是自己組裝的方式——理解各元件的配置，之後要用 Caelestia 或自己拼都能做。

## Waybar：狀態列

Waybar 是 Hyprland 桌面最常用的狀態列。配置在 `~/.config/waybar/`，分兩個檔案：`config.jsonc`（結構和模組）和 `style.css`（外觀）。

### 結構配置

```jsonc
// ~/.config/waybar/config.jsonc
{
    "layer": "top",
    "position": "top",
    "height": 36,
    "spacing": 4,

    // 左中右三區塊各放哪些模組
    "modules-left": ["hyprland/workspaces", "hyprland/window"],
    "modules-center": ["clock"],
    "modules-right": ["pulseaudio", "network", "cpu", "memory", "battery", "tray"],

    // 各模組設定
    "hyprland/workspaces": {
        "format": "{id}",
        "on-click": "activate"
    },
    "clock": {
        "format": "{:%H:%M}",
        "format-alt": "{:%Y-%m-%d %H:%M}",
        "tooltip-format": "<tt>{calendar}</tt>"
    },
    "battery": {
        "format": "{capacity}% {icon}",
        "format-icons": ["", "", "", "", ""],
        "states": {
            "warning": 30,
            "critical": 15
        }
    },
    "network": {
        "format-wifi": "{essid} ({signalStrength}%)",
        "format-ethernet": "{ifname}",
        "format-disconnected": "Disconnected"
    },
    "pulseaudio": {
        "format": "{volume}%",
        "on-click": "pavucontrol"
    }
}
```

`format` 欄位裡的 icon 字元來自 Nerd Font——[終端機與編輯器](/dotfile/03-terminal-ecosystem/)提到的字型安裝是這裡正常顯示的前提。

### 外觀 CSS

```css
/* ~/.config/waybar/style.css */

* {
    font-family: "JetBrainsMono Nerd Font", monospace;
    font-size: 13px;
}

window#waybar {
    background-color: rgba(30, 30, 46, 0.85);
    color: #cdd6f4;
}

#workspaces button {
    padding: 0 8px;
    color: #6c7086;
    border-radius: 6px;
}

#workspaces button.active {
    color: #cdd6f4;
    background: rgba(137, 180, 250, 0.2);
}

#clock, #battery, #network, #pulseaudio {
    padding: 0 10px;
}

#battery.warning {
    color: #f9e2af;
}

#battery.critical {
    color: #f38ba8;
}
```

CSS 裡的色碼（`#cdd6f4`、`#89b4fa`、`#f38ba8`）來自配色方案（這個範例用的是 Catppuccin Mocha）。統一使用同一套色碼是 rice 視覺協調的基礎。

## Wofi / Rofi：啟動器

啟動器是按快捷鍵彈出的搜尋框，用來啟動應用程式、執行指令、搜尋檔案。

Wofi（Wayland 原生）配置：

```ini
# ~/.config/wofi/config
show=drun
width=600
height=400
prompt=Search...
insensitive=true
allow_markup=true
```

```css
/* ~/.config/wofi/style.css */
window {
    background-color: #1e1e2e;
    border: 2px solid #89b4fa;
    border-radius: 12px;
}

#input {
    background-color: #313244;
    color: #cdd6f4;
    border-radius: 8px;
    margin: 10px;
    padding: 8px 12px;
}

#entry:selected {
    background-color: rgba(137, 180, 250, 0.2);
}
```

Rofi（需要 wayland fork rofi-lbonn-wayland）功能更豐富——支援多種 mode（drun、window、ssh、自定義 script）、主題系統更完整。如果需要進階功能（例如 emoji picker、密碼管理器整合），Rofi 是更好的選擇。

## Mako / Dunst：通知

Mako 是 Wayland 原生的通知 daemon，配置簡潔：

```ini
# ~/.config/mako/config
font=JetBrainsMono Nerd Font 11
background-color=#1e1e2e
text-color=#cdd6f4
border-color=#89b4fa
border-radius=8
border-size=2
padding=12
default-timeout=5000
max-visible=3

[urgency=critical]
border-color=#f38ba8
default-timeout=0
```

通知的視覺風格（圓角、配色、字型）要跟 waybar 和啟動器一致，這是整體 rice 不散的關鍵。
