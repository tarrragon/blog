---
title: "Caelestia 安裝"
date: 2026-06-29
description: "要在 Arch Linux 上安裝 Caelestia 桌面 shell 時回來讀"
weight: 4
tags: ["dotfile", "rice", "caelestia", "arch", "hyprland"]
---

Caelestia 的安裝有兩條路：用 CLI 工具一鍵部署完整 dotfiles，或只安裝 shell 元件保留自己的 Hyprland 配置。兩者的前提都是 Hyprland 已經安裝且能正常啟動。

## 前提條件

- Arch Linux（或 Arch 系發行版如 CachyOS、EndeavourOS）
- Hyprland 已安裝且能從 TTY 啟動（見 [Hyprland 安裝指南](/linux/dotfile/05-hyprland-config/hyprland-installation/)）
- AUR helper 已安裝（yay 或 paru）
- 網路連線（安裝過程需要拉 AUR 套件和 Git repo）

## 推薦方式：CLI 完整安裝

```bash
paru -S caelestia-cli
caelestia install
```

`caelestia install` 做的事：

1. 從 GitHub clone Caelestia dotfiles repo
2. 安裝所有 runtime 依賴（透過 AUR helper）
3. 部署配置檔到 `~/.config/` 對應位置
4. 設定 Hyprland 載入 Caelestia shell

安裝完成後重新啟動 Hyprland，Caelestia 會自動載入。

**注意**：`caelestia install` 會覆寫你現有的 Hyprland 配置。如果你已經有自己的 hyprland.conf / hyprland.lua，先備份。安裝後可以透過 `~/.config/caelestia/hypr-user.lua` 加入自訂設定。

## Shell-only 安裝

只裝 UI 元件，不動 Hyprland config 和其他應用程式設定：

```bash
yay -S caelestia-shell
```

啟動方式：

```bash
caelestia shell -d    # daemonized，背景執行
# 或
qs -c caelestia       # 透過 quickshell 直接啟動
```

把啟動指令加進 Hyprland 的 `exec-once`（Lua 格式）：

```lua
hl.config({
    exec_once = {
        "caelestia shell -d",
    },
})
```

## AUR 套件一覽

| 套件                  | 說明                                     |
| --------------------- | ---------------------------------------- |
| `caelestia-shell`     | 穩定版 shell（UI 元件）                  |
| `caelestia-shell-git` | 開發版 shell（最新功能，可能不穩定）     |
| `caelestia-cli`       | CLI 工具（安裝、主題切換、截圖、錄影等） |

`caelestia-cli` 依賴 `caelestia-shell`，安裝 CLI 會自動拉 shell。

## 手動 Build

從原始碼 build shell（不使用 AUR）：

```bash
cd "$XDG_CONFIG_HOME/quickshell"
git clone https://github.com/caelestia-dots/shell.git caelestia
cd caelestia
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/
cmake --build build
sudo cmake --install build
```

## Runtime 依賴

### Shell 依賴

| 套件                    | 用途                            |
| ----------------------- | ------------------------------- |
| quickshell-git          | Quickshell 框架（穩定版不夠用） |
| ddcutil                 | 外接螢幕亮度控制                |
| brightnessctl           | 筆電螢幕亮度                    |
| libcava                 | 音訊視覺化                      |
| networkmanager          | 網路管理                        |
| lm-sensors              | 硬體溫度感測                    |
| fish                    | Fish shell（部分功能依賴）      |
| aubio                   | 音訊分析                        |
| libpipewire             | PipeWire 音訊整合               |
| qt6-declarative         | QML runtime                     |
| material-symbols (font) | Material Design icon 字型       |
| caskaydia-cove-nerd     | Nerd Font                       |

**quickshell-git 是硬性需求**。穩定版的 quickshell 缺少 Caelestia 需要的 API，安裝穩定版會導致 shell 無法啟動。

### CLI 依賴

| 套件                | 用途         |
| ------------------- | ------------ |
| libnotify           | 通知發送     |
| swappy              | 截圖標註     |
| grim                | Wayland 截圖 |
| dart-sass           | SCSS 編譯    |
| wl-clipboard        | 剪貼簿       |
| slurp               | 區域選取     |
| gpu-screen-recorder | 螢幕錄影     |
| glib2               | GLib 工具    |
| cliphist            | 剪貼簿歷史   |
| fuzzel              | 模糊搜尋選單 |

## 登入管理器

Caelestia 不含登入管理器。推薦用 greetd + tuigreet：

```bash
sudo pacman -S greetd greetd-tuigreet
```

`/etc/greetd/config.toml`：

```toml
[terminal]
vt = 1

[default_session]
command = "tuigreet --cmd Hyprland"
user = "greeter"
```

```bash
sudo systemctl enable greetd
```

也可以不裝登入管理器，直接從 TTY 啟動：

```bash
# 登入 TTY 後
Hyprland
```

## Full Dotfiles 管理範圍

`caelestia install` 部署的完整 dotfiles 不只是 shell，還包括：

- Hyprland config（Lua 格式）
- Firefox / Zen Browser 設定
- VSCode / Zed 設定
- Fish shell config
- Foot terminal config
- Starship prompt
- Btop
- Fastfetch
- Thunar 檔案管理器

這是 Caelestia 「一套 rice」的完整範圍。如果你只想用 shell 元件、保留自己的應用程式配置，用 shell-only 安裝。

## CLI 常用指令

| 指令                              | 功能                 |
| --------------------------------- | -------------------- |
| `caelestia shell -d`              | 啟動 shell（背景）   |
| `caelestia shell -s`              | 列出所有 IPC 指令    |
| `caelestia install`               | 完整安裝 dotfiles    |
| `caelestia update`                | 系統 + dotfiles 更新 |
| `caelestia scheme set -n dynamic` | 設定動態配色方案     |
| `caelestia wallpaper -f <path>`   | 設定桌布             |
| `caelestia screenshot`            | 截圖                 |
| `caelestia record`                | 螢幕錄影             |
| `caelestia clipboard`             | 剪貼簿歷史           |
| `caelestia emoji`                 | Emoji / glyph 選取器 |
| `caelestia toggle`                | 切換特殊工作區       |
| `caelestia resizer`               | 視窗 resize daemon   |

## 首次啟動常見問題

**黑屏**：通常是缺少 `xdg-desktop-portal-hyprland`。確認已安裝：

```bash
pacman -Q xdg-desktop-portal-hyprland
```

**Shell 沒有載入**：確認 quickshell-git（不是 quickshell 穩定版）已安裝，且 Hyprland 的 exec-once 有啟動 Caelestia。

**字型 icon 顯示為方塊**：缺少 Material Symbols 和 Nerd Font。安裝：

```bash
yay -S material-symbols ttf-caskaydia-cove-nerd
```

## VM 測試 vs 實機測試

**VM 可測試**：安裝流程完整性、CLI 指令是否正常、配置檔結構和語法、啟動器功能、通知系統行為、配置 reload。

**需實機測試**：動畫流暢度和幀率、blur 品質和效能影響、Material Design 3 動態取色品質、多螢幕佈局、daily-use 的回應速度和穩定性。

VM 中 Caelestia 的 blur、動畫、動態取色會極度降級或無法運作（軟體渲染沒有足夠的 GPU 加速）。VM 適合驗證「裝得起來、config 能讀」，不適合評估視覺效果和日常使用體驗。
