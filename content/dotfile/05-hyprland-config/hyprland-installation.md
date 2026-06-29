---
title: "Hyprland 安裝與環境建置"
date: 2026-06-29
description: "要在 Arch Linux 上從零安裝 Hyprland 桌面環境時回來讀"
weight: 1
tags: ["dotfile", "hyprland", "arch-linux", "installation", "gpu"]
---

Hyprland 的安裝分三層：compositor 本身、GPU 驅動、桌面配套工具。Compositor 只負責視窗管理和畫面合成，其餘功能（status bar、launcher、通知、音訊、藍牙、網路）都需要另外裝。本篇以 Arch Linux 為主要說明對象，其他發行版在最後簡述。

## 核心套件

```bash
sudo pacman -S hyprland xorg-xwayland xdg-desktop-portal-hyprland
```

| 套件                          | 角色                                                             |
| ----------------------------- | ---------------------------------------------------------------- |
| `hyprland`                    | Compositor 本體，在 Arch 官方 `extra` repo，不需要 AUR           |
| `xorg-xwayland`               | X11 相容層，讓舊 X11 應用程式在 Wayland 環境裡正常運行           |
| `xdg-desktop-portal-hyprland` | Hyprland 專屬的 portal backend，處理 screen sharing 和檔案對話框 |

> **[VM 可測試]** 套件安裝本身在 VM 和實機上完全相同。

## GPU 驅動

GPU 驅動決定 Hyprland 的渲染是走硬體加速還是軟體 fallback。AMD 和 Intel 開箱即用，NVIDIA 需要額外配置。

### AMD（推薦，開箱即用）

```bash
sudo pacman -S mesa vulkan-radeon libva-mesa-driver mesa-vdpau
```

mkinitcpio MODULES 加入：`amdgpu`

環境變數（放在 Hyprland 配置裡）：

```lua
env = {
    "LIBVA_DRIVER_NAME, radeonsi",
    "VDPAU_DRIVER, radeonsi",
    "AMD_VULKAN_ICD, RADV",
}
```

AMD 是 Hyprland / Wayland 生態支援最好的 GPU。如果是新購硬體、有選擇的餘地，AMD 是最省事的選項。

### Intel（開箱即用）

```bash
sudo pacman -S mesa vulkan-intel intel-media-driver
```

mkinitcpio MODULES 加入：`i915`

```lua
env = {
    "LIBVA_DRIVER_NAME, iHD",
    "VDPAU_DRIVER, va_gl",
}
```

Intel 內顯在 Wayland 上表現穩定，適合筆電和輕度桌面使用。

### NVIDIA（需要額外配置，非官方支援）

> **[需實機測試]** NVIDIA 的所有設定在 VM 中無意義——VM 使用 virtio-gpu 或軟體渲染，不走 NVIDIA 驅動。以下步驟只在實體機有 NVIDIA 顯卡時才需要。

Hyprland 官方不支援 NVIDIA，但社群有成熟的 workaround。最低版本需求：

- NVIDIA driver >= 555
- xorg-xwayland >= 24.1
- wayland-protocols >= 1.34

安裝：

```bash
sudo pacman -S nvidia-dkms nvidia-utils libva-nvidia-driver
# 32-bit 支援（遊戲可能需要）：
sudo pacman -S lib32-nvidia-utils
```

mkinitcpio MODULES（依硬體配置選擇）：

純 NVIDIA 桌機：

```text
MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)
```

Intel + NVIDIA hybrid 筆電（Intel 排在 NVIDIA 前面）：

```text
MODULES=(i915 nvidia nvidia_modeset nvidia_uvm nvidia_drm)
```

更新 initramfs：

```bash
sudo mkinitcpio -P
```

Modprobe 設定：

```text
# /etc/modprobe.d/nvidia.conf
options nvidia_drm modeset=1
```

GRUB kernel parameter：

```text
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="... nvidia_drm.modeset=1 nvidia_drm.fbdev=1"
```

更新 GRUB：

```bash
sudo grub-mkconfig -o /boot/grub/grub.cfg
```

Hyprland 配置裡的 NVIDIA 環境變數：

```lua
env = {
    "LIBVA_DRIVER_NAME, nvidia",
    "__GLX_VENDOR_LIBRARY_NAME, nvidia",
    "GBM_BACKEND, nvidia-drm",         -- 如果 Firefox crash，移除這行
    "NVD_BACKEND, direct",
}
```

Cursor 修正（NVIDIA 常見的硬體 cursor 問題）：

```lua
hl.config({
    cursor = {
        no_hardware_cursors = true,
        allow_dumb_copy = true,
    },
})
```

Suspend/resume 支援：

```bash
sudo systemctl enable nvidia-suspend.service nvidia-hibernate.service nvidia-resume.service
```

### 檢查 GPU 驅動狀態

```bash
lspci -k | grep -A 3 VGA        # 查看使用中的驅動
glxinfo | grep "OpenGL renderer" # 查看活躍的 renderer
vulkaninfo --summary             # Vulkan 裝置資訊
```

## 桌面配套套件

Hyprland 只管視窗，以下是一個可用桌面需要的配套工具：

```bash
sudo pacman -S \
  kitty waybar wofi mako \
  polkit-gnome grim slurp wl-clipboard cliphist \
  hyprpaper hyprlock hypridle \
  pipewire pipewire-alsa pipewire-jack pipewire-pulse wireplumber \
  pamixer pavucontrol brightnessctl \
  bluez bluez-utils blueman \
  networkmanager network-manager-applet \
  thunar gvfs \
  qt5-wayland qt6-wayland \
  ttf-jetbrains-mono-nerd noto-fonts noto-fonts-cjk
```

| 類別     | 套件                                          | 用途                                      |
| -------- | --------------------------------------------- | ----------------------------------------- |
| 終端機   | `kitty`                                       | Hyprland 預設配置使用的 terminal emulator |
| 狀態列   | `waybar`                                      | JSON config + CSS styling 的 status bar   |
| 啟動器   | `wofi`                                        | Wayland 原生 app launcher                 |
| 通知     | `mako`                                        | 輕量 notification daemon                  |
| 認證代理 | `polkit-gnome`                                | GUI 權限提升（sudo 對話框）               |
| 截圖     | `grim` + `slurp`                              | 截圖工具 + 選區工具                       |
| 剪貼簿   | `wl-clipboard` + `cliphist`                   | 剪貼簿存取 + 歷史記錄                     |
| 桌布     | `hyprpaper`                                   | 靜態桌布                                  |
| 鎖屏     | `hyprlock`                                    | Hyprland 配套鎖屏                         |
| Idle     | `hypridle`                                    | 閒置偵測（觸發鎖屏/休眠）                 |
| 音訊     | `pipewire` + `wireplumber` + `pipewire-pulse` | 音訊 server（取代 PulseAudio）            |
| 音量控制 | `pamixer`（CLI）+ `pavucontrol`（GUI）        | 音量調整                                  |
| 亮度     | `brightnessctl`                               | 螢幕亮度（筆電）                          |
| 藍牙     | `bluez` + `bluez-utils` + `blueman`           | 藍牙協定 + GUI 管理                       |
| 網路     | `networkmanager` + `nm-applet`                | 網路管理 + system tray 圖示               |
| 檔案管理 | `thunar` + `gvfs`                             | 圖形檔案管理器 + 回收筒/遠端掛載          |
| Qt 相容  | `qt5-wayland` + `qt6-wayland`                 | Qt 應用在 Wayland 下正常運行              |
| 字型     | `ttf-jetbrains-mono-nerd` + `noto-fonts-cjk`  | Nerd Font（waybar icon 需要）+ CJK 字型   |

AUR 補充套件（用 `yay` 或 `paru`）：

```bash
yay -S grimblast-git   # Hyprland 截圖 wrapper
yay -S swww            # 動態桌布（hyprpaper 的替代）
yay -S rofi-wayland    # 功能比 wofi 更豐富的 launcher
```

> **[VM 可測試]** 套件安裝在 VM 中完全可執行。waybar、wofi、mako 在軟體渲染下也能正常使用。
>
> **[需實機測試]** 藍牙（`bluez`）、亮度（`brightnessctl`）、音訊裝置偵測（`pipewire`）需要實際硬體。

## 登入管理器

Hyprland 預設不含登入管理器。三個選項：

### 從 TTY 直接啟動（最簡單）

登入文字介面後直接執行 `Hyprland`。建議用 wrapper script 設定必要的環境變數：

```bash
#!/bin/sh
# ~/start-hyprland.sh
export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=Hyprland
export XDG_SESSION_DESKTOP=Hyprland
exec Hyprland
```

```bash
chmod +x ~/start-hyprland.sh
~/start-hyprland.sh
```

### greetd + tuigreet（推薦）

greetd 是一個輕量的登入管理器，tuigreet 是它的 TUI 前端：

```bash
sudo pacman -S greetd greetd-tuigreet
```

設定 `/etc/greetd/config.toml`：

```toml
[terminal]
vt = 1

[default_session]
command = "tuigreet --cmd Hyprland"
user = "greeter"
```

自動登入（可選）：

```toml
[initial_session]
command = "Hyprland"
user = "yourusername"
```

啟用服務：

```bash
sudo systemctl enable greetd
```

### SDDM

如果已經有 KDE 或偏好圖形化登入介面：

```bash
sudo pacman -S sddm
sudo systemctl enable sddm
```

SDDM 會自動偵測到 Hyprland 並在登入畫面顯示它作為 session 選項。

> **[VM 可測試]** 登入管理器的設定在 VM 中可完整測試。

## 首次啟動常見問題

| 症狀                           | 原因                                     | 修正                                                        |
| ------------------------------ | ---------------------------------------- | ----------------------------------------------------------- |
| 黑屏、沒有 cursor              | 缺少 polkit agent 或 seatd service       | `sudo systemctl enable --now seatd` 或安裝 `polkit-gnome`   |
| 開不了 terminal                | 預設 keybind 用的是 kitty，但 kitty 沒裝 | `sudo pacman -S kitty` 或改 keybind 指向已安裝的 terminal   |
| Cursor 不見（NVIDIA）          | 硬體 cursor 問題                         | 設定 `cursor { no_hardware_cursors = true }`                |
| Portal 衝突，screen share 失敗 | 同時裝了多個 portal backend              | 移除 `xdg-desktop-portal-gnome` 和 `xdg-desktop-portal-gtk` |
| 沒有音訊                       | PipeWire 服務未啟動                      | `systemctl --user enable --now pipewire wireplumber`        |
| Config 報錯但不影響使用        | 自動產生的預設 config 語法不完整         | emergency keybind 仍可用：SUPER+Q 開 terminal、SUPER+M 離開 |

## 配置格式：Lua 取代 hyprlang（v0.55+）

Hyprland v0.55（2026 年 4 月）起，配置格式從 hyprlang（`.conf`）遷移到 **Lua**（`.lua`）。舊的 `hyprland.conf` 在沒有 `.lua` 檔案時仍然可用，但 hyprlang 已被標記為 deprecated，預計在後續版本移除。

| 格式           | 檔案                           | 狀態       |
| -------------- | ------------------------------ | ---------- |
| Lua（新）      | `~/.config/hypr/hyprland.lua`  | 推薦       |
| hyprlang（舊） | `~/.config/hypr/hyprland.conf` | deprecated |

遷移工具：`hyprlang2lua`（Go，有瀏覽器版）、`hyprconf2lua`（Python pip）、`hypr-migrate`。

本系列後續文章（模組五的其他篇章、模組六的 Caelestia）都使用 Lua 格式。如果在網路上看到 `.conf` 格式的教學，多數仍然可用，但建議儘早遷移到 Lua。

拆分配置用 Lua 原生的 `require()`：

```lua
-- hyprland.lua
require("keybinds")    -- 載入同目錄下的 keybinds.lua
require("rules")       -- 載入同目錄下的 rules.lua
require("appearance")
```

詳細的配置語法和設定邏輯在[核心配置](/dotfile/05-hyprland-config/hyprland-core-config/)和 [Workspace、Window Rules 與外觀](/dotfile/05-hyprland-config/workspace-rules-appearance/)。

## 其他發行版

### Fedora

Fedora 39 起即在官方 repo。安裝：

```bash
sudo dnf install hyprland
```

JaKooLit 提供自動化安裝腳本（`github.com/JaKooLit/Fedora-Hyprland`），Fedora 42+ 運作良好。

### NixOS

NixOS 有官方 module，在 `configuration.nix` 加入：

```nix
programs.hyprland.enable = true;
```

Home Manager 也有對應 module，可以宣告式管理 Hyprland 配置。

### Ubuntu

不推薦。Ubuntu 的 point-release 模型跟 Hyprland 的 bleeding-edge 更新節奏衝突。沒有官方 PPA，從 source 編譯可行但維護成本高。如果一定要用 Debian 系，Arch 的 rolling release 或 Fedora 的半年週期更適合 Hyprland。

## 安裝後的下一步

安裝完成後，VM 環境的額外設定（環境變數、效能調整、測試矩陣）見 [VM 環境設定與測試矩陣](/dotfile/05-hyprland-config/hyprland-vm-setup/)。配置檔的組織方式和 keybind 設計見 [Hyprland 核心配置](/dotfile/05-hyprland-config/hyprland-core-config/)。
