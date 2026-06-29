---
title: "配色系統、鎖屏與 GTK 主題"
date: 2026-06-29
description: "桌面配色散亂看起來雜、或要換主題不知道該改哪些檔案時回來讀"
weight: 2
tags: ["dotfile", "rice", "hyprlock", "catppuccin", "gtk", "linux"]
---

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
