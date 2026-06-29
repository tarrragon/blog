---
title: "模組六：桌面 Rice 設計"
date: 2026-06-29
description: "Hyprland 桌面從能用到好看好用 — 狀態列、啟動器、通知、鎖屏、配色系統的設計與配置"
tags: ["dotfile", "rice", "waybar", "hyprland", "linux"]
---

Rice 在 Linux 桌面社群指的是桌面視覺客製化——把系統外觀調教成個人化的美學呈現。這個詞源自汽車改裝文化（Race Inspired Cosmetic Enhancements 的逆向縮寫），在 Linux 圈已轉為中性的圈內用語，r/unixporn 社群就是圍繞這件事運轉的。

模組五教了 Hyprland compositor 本身的配置（平鋪邏輯、keybind、workspace）。這個模組處理的是 compositor 之上的「桌面 shell」層——狀態列、啟動器、通知、鎖屏、桌布、配色系統。這些元件各自是獨立的小工具，用配置檔組合成一套協調的桌面體驗。

## 桌面 Shell 的組成

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

`format` 欄位裡的 icon 字元來自 Nerd Font——模組三提到的字型安裝是這裡正常顯示的前提。

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

## Hyprlock：鎖屏

Hyprlock 是 Hyprland 配套的鎖屏工具，支援模糊背景、自定義佈局：

```bash
# ~/.config/hypr/hyprlock.conf

background {
    monitor =
    path = screenshot
    blur_passes = 3
    blur_size = 8
}

input-field {
    monitor =
    size = 250, 50
    outline_thickness = 2
    outer_color = rgba(137, 180, 250, 1)
    inner_color = rgba(30, 30, 46, 1)
    font_color = rgba(205, 214, 244, 1)
    placeholder_text = <i>Password...</i>
    fade_on_empty = true
    position = 0, -50
    halign = center
    valign = center
}

label {
    monitor =
    text = $TIME
    font_size = 64
    font_family = JetBrainsMono Nerd Font
    color = rgba(205, 214, 244, 1)
    position = 0, 80
    halign = center
    valign = center
}
```

## 配色系統的統一管理

Rice 的視覺品質取決於配色一致性。散亂的色碼（waybar 用一套、wofi 用另一套、mako 又一套）是桌面看起來「雜」的最常見原因。

管理方式：

**選定一套配色方案**。Catppuccin、Tokyo Night、Gruvbox、Nord 是目前最多 Linux ricer 使用的方案，每一套都有完整的色彩定義和各工具的預設配置。

**建立配色變數檔**。把色碼集中到一個檔案，其他配置引用它：

```bash
# ~/.config/hypr/colors.conf
$rosewater = rgb(f5e0dc)
$flamingo  = rgb(f2cdcd)
$pink      = rgb(f5c2e7)
$mauve     = rgb(cba6f7)
$red       = rgb(f38ba8)
$maroon    = rgb(eba0ac)
$peach     = rgb(fab387)
$yellow    = rgb(f9e2af)
$green     = rgb(a6e3a1)
$teal      = rgb(94e2d5)
$sky       = rgb(89dceb)
$sapphire  = rgb(74c7ec)
$blue      = rgb(89b4fa)
$lavender  = rgb(b4befe)
$text      = rgb(cdd6f4)
$subtext1  = rgb(bac2de)
$overlay0  = rgb(6c7086)
$surface0  = rgb(313244)
$base      = rgb(1e1e2e)
$mantle    = rgb(181825)
$crust     = rgb(11111b)
```

Hyprland 的 `source` 可以引用這些變數。Waybar 和 Wofi 的 CSS 無法直接引用 Hyprland 變數，但可以用 build script 或 template 工具（如 pywal、flavours）從一份主設定產生各工具的配色。

**換配色方案**時需要改的檔案清單：

- Hyprland appearance.conf（邊框、陰影顏色）
- Waybar style.css
- Wofi/Rofi style.css
- Mako config
- Hyprlock config
- Terminal emulator 配色
- Neovim colorscheme
- GTK theme（影響 GUI 應用程式的外觀）

把這個清單記在 dotfile repo 的 README 裡，換主題時有對照不會漏改。

## GTK / Qt 主題

Linux 的 GUI 應用程式分兩大陣營：GTK（GNOME 系）和 Qt（KDE 系）。平鋪式 WM 不自帶主題引擎，需要手動設定：

```bash
# GTK 設定
# ~/.config/gtk-3.0/settings.ini
[Settings]
gtk-theme-name=Catppuccin-Mocha-Standard-Blue-Dark
gtk-icon-theme-name=Papirus-Dark
gtk-font-name=Noto Sans CJK TC 11
gtk-cursor-theme-name=Bibata-Modern-Classic
```

Qt 應用程式用 `qt5ct` / `qt6ct` 設定，或用 Kvantum 主題引擎統一風格。

## Dotfile 結構對應

```text
~/dotfiles/
├── waybar/
│   └── .config/
│       └── waybar/
│           ├── config.jsonc
│           └── style.css
├── wofi/
│   └── .config/
│       └── wofi/
│           ├── config
│           └── style.css
├── mako/
│   └── .config/
│       └── mako/
│           └── config
├── hyprlock/
│   └── .config/
│       └── hypr/
│           └── hyprlock.conf
├── gtk/
│   └── .config/
│       └── gtk-3.0/
│           └── settings.ini
└── themes/
    └── colors.conf          # 集中配色定義
```

## Rice 的投資報酬判讀

Rice 可以投入的時間沒有上限。務實的分界線：

- **功能性配置**（waybar 顯示正確資訊、wofi 能搜到 app、通知會跳出來）：投入一到兩小時，這是桌面可用的前提
- **視覺統一**（全域配色一致、字型統一、圓角/間距協調）：投入半天到一天，這是「好看」跟「雜亂」的分界
- **精雕細節**（自定義動畫曲線、pixel-perfect 對齊、自製 widget）：時間無底洞，看個人興趣

前兩層是值得做的——它們改善每天使用的體驗。第三層是嗜好領域，跟「把車改到完美」是同一種動力，不需要理性上的正當性。
