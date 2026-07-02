---
title: "Hyprland VM 環境設定與測試矩陣"
date: 2026-06-29
description: "要在 VM 裡測試 Hyprland 配置、或判斷某個設定該在 VM 還是實機驗證時回來讀"
weight: 4
tags: ["dotfile", "hyprland", "vm", "utm", "testing"]
---

VM 是 Hyprland 配置的演練場——用來驗證「配置邏輯對不對」，不是用來體驗「跑起來順不順」。GPU 加速在 VM 中受限，動畫和模糊效果會嚴重降級或無法使用，但配置檔語法、keybind 設計、window rules、workspace 邏輯都能在 VM 中完整測試。

## UTM on Apple Silicon 設定

Apple Silicon Mac 用 UTM（基於 QEMU）跑 ARM64 Linux VM：

- **CPU**：UTM 使用 Apple Hypervisor.framework，ARM64 guest 接近原生速度
- **GPU**：使用 `virtio-gpu-gl-pci`（UTM v4.1+ 新建 Linux VM 的預設）。UTM v5.0.0+ 的 GitHub release 版支援 Venus driver（guest Mesa → host MoltenVK → Apple Metal 的 Vulkan 轉送路徑），這是目前最好的 GPU 加速方案
- **Linux ISO**：Arch Linux ARM（archlinuxarm.org）或 Fedora aarch64
- **建議配置**：4 CPU cores、4GB+ RAM、40GB+ disk

### UTM 建 VM 的注意事項

- **第一頁選 Virtualize，不是 Emulate**——同架構（Apple Silicon 跑 ARM64 guest）兩條都是 QEMU，差在 Virtualize 走 hvf 硬體虛擬化（CPU 接近原生）、Emulate 走 TCG 純軟體模擬（CPU 慢一個數量級；實測 C++ 大型編譯一小時只跑 1/3）。Emulate 只在跨架構（ARM Mac 跑 x86_64 guest）才需要。判別現有 VM：guest 裡 `lscpu` 的 Model name 是 `-` 為直通、顯示具體型號（如 Cortex-A72）為模擬
- 選 「Linux」 虛擬機類型，不是 「Other」
- Display Card 選 `virtio-gpu-gl-pci`（有 3D 加速），不是 `virtio-gpu-pci`（無加速）；Emulate 精靈預設給無加速的 `virtio-gpu-pci`、Virtualize 精靈通常直接給對
- 如果用 App Store 版的 UTM（不含 Venus），只有基本的 virtio-gpu-gl 加速
- GitHub release 版的 UTM 支援 Venus/MoltenVK，效能更好但仍不及裸金屬

## VM 必要環境變數

在 Hyprland 配置裡加入以下環境變數（只在 VM 中使用，實機要移除）：

```lua
-- VM-only environment variables
env = {
    "WLR_RENDERER_ALLOW_SOFTWARE, 1",  -- 允許軟體渲染 fallback
    "WLR_NO_HARDWARE_CURSORS, 1",      -- 停用硬體 cursor（VM 常見問題）
    "LIBGL_ALWAYS_SOFTWARE, 1",        -- 強制 Mesa 軟體渲染
}
```

如果上述仍無法啟動（virtio-gpu vGPU passthrough 的情況）：

```lua
env = {
    "AQ_NO_KMS_REQUIREMENT, 1",       -- 繞過 KMS 需求
    "WLR_RENDERER, pixman",            -- 強制 pixman 軟體 renderer
}
```

> **[已驗證]** Hyprland 0.55（Aquamarine）+ UTM virtio-gpu-gl-pci 實測：GPU 加速模式下 Hyprland 直接走 VirGL/Venus，不需要 `WLR_RENDERER` 或 `WLR_RENDERER_ALLOW_SOFTWARE`。`AQ_NO_KMS_REQUIREMENT` 仍有效。軟體渲染 fallback 路徑（`WLR_RENDERER=pixman`）未測試——有 GPU 加速時不需要走這條。

## VM 中應該關閉的效果

軟體渲染下，視覺效果是最大的效能殺手。建議在 VM 配置中停用：

```lua
hl.config({
    decoration = {
        blur = { enabled = false },     -- 模糊是 GPU 最重的效果
        shadow = { enabled = false },
        rounding = 0,
    },
    animations = {
        enabled = false,                -- 或設定極簡動畫
    },
})
```

這些效果關閉後，基本的平鋪操作（切換視窗、移動 workspace、開關 app）在 VM 中應該足夠流暢。

## 效能預期

| 功能              | 軟體渲染 | virtio-gpu-gl | 裸金屬（實機） |
| ----------------- | -------- | ------------- | -------------- |
| 基本平鋪操作      | 可用     | 順暢          | 順暢           |
| 視窗動畫          | 卡頓明顯 | 勉強可接受    | 流暢           |
| 模糊/透明         | 無法使用 | 卡頓          | 流暢           |
| Waybar + Wofi     | 正常     | 正常          | 正常           |
| 多 Workspace 切換 | 正常     | 正常          | 正常           |
| Firefox 瀏覽      | 明顯變慢 | 可用          | 正常           |

VM 的價值在於驗證配置邏輯，不在於評估視覺體驗。如果在 VM 裡覺得「卡」，不代表 Hyprland 本身慢——多數情況是 VM 圖形加速的限制。

## Sway 作為 VM 初步驗證工具

如果 VM 中 Hyprland 跑得太吃力，可以先用 Sway 驗證 VM 的 Wayland 圖形棧是否正常：

```bash
sudo pacman -S sway foot
sway
```

Sway 比 Hyprland 輕量（基於 wlroots、沒有華麗動畫），如果 Sway 能跑，代表 VM 的 Wayland 環境是正常的，Hyprland 的問題只是效能不夠。如果連 Sway 都跑不動，要回去檢查 VM 的 GPU 設定。

## VM vs 實機測試矩陣

### VM 中可完整驗證

| 項目               | 說明                                                   |
| ------------------ | ------------------------------------------------------ |
| 配置檔語法         | Lua config 是否解析正確、require 拆分是否正常          |
| Keybind 設計       | 快捷鍵邏輯、submap、modifier 組合                      |
| Window rules       | float / workspace assignment / opacity 規則是否生效    |
| Workspace 切換     | workspace 編號、切換邏輯                               |
| Layout 選擇        | dwindle vs master 的行為差異                           |
| Waybar 模組配置    | JSON config + CSS styling 是否正確顯示                 |
| Wofi/Rofi 主題     | 啟動器的功能和外觀設定                                 |
| Mako 通知樣式      | 通知的位置、配色、timeout                              |
| Hyprlock 佈局      | 鎖屏的輸入框位置和文字配置                             |
| Autostart 順序     | exec-once 的程式是否正確啟動                           |
| 環境變數           | XDG、Qt、GTK 等環境變數是否正確設定                    |
| Stow 部署          | dotfile repo 的 stow 是否正確建立 symlink              |
| Bootstrap script   | install.sh 的完整流程（安裝套件 + deploy 配置）        |
| Caelestia CLI 指令 | `caelestia shell`、`caelestia scheme` 等指令是否可執行 |

### 需要實機測試

| 項目                       | 為什麼 VM 不行                                 |
| -------------------------- | ---------------------------------------------- |
| 多螢幕配置                 | VM 通常只有一個虛擬顯示器                      |
| HiDPI / fractional scaling | 虛擬顯示器不模擬真實解析度行為                 |
| VRR / Adaptive Sync        | 需要支援 VRR 的真實螢幕                        |
| 動畫流暢度                 | VM 的 GPU 加速不足以評估真實效能               |
| 模糊效果品質               | 軟體渲染下模糊不可用或品質差                   |
| 觸控板 / 手勢              | VM 沒有觸控板裝置                              |
| 媒體鍵 / 亮度鍵            | 需要實體鍵盤上的 XF86 keycodes                 |
| NVIDIA 驅動設定            | VM 不走 NVIDIA 驅動，所有 NVIDIA 配置無法測試  |
| Screen sharing             | PipeWire + portal 的完整鏈路在 VM 中測試無意義 |
| Suspend / Resume           | 虛擬機的 suspend 行為跟實機不同                |
| 硬體 cursor 渲染           | VM 用軟體 cursor，無法測試硬體 cursor 問題     |
| 藍牙 / WiFi 整合           | 需要實際硬體                                   |
| 電池 / 電源管理            | 筆電專屬功能                                   |
| 日常使用效能               | 只有在實機跑一段時間才能評估「能不能當主力」   |

## 務實的 VM 使用策略

VM 階段的目標是「把配置寫好、驗證邏輯、確認 bootstrap script 能跑」，不是「體驗 Hyprland 好不好用」。具體做法：

1. 在 VM 中完成 Arch Linux 安裝 + Hyprland 套件安裝（怎麼把那台 Linux 從 ISO 裝起來、安裝程式選項怎麼判讀、裝完怎麼驗工具與連入，見 [Linux 安裝與機器初始化](/linux/install/)）
2. 關閉所有視覺效果（blur / animation / shadow）
3. 寫好完整的 Hyprland 配置（keybind / rules / workspace / autostart）
4. 寫好 waybar / wofi / mako 配置
5. 測試 stow 部署流程（從 dotfile repo clone → stow → 配置生效）
6. 測試 bootstrap script（install.sh 從零到完整桌面）
7. 把驗證過的配置 commit 進 dotfile repo

到實機時，clone dotfile repo → 跑 install.sh → 補上硬體相關設定（monitor、GPU 驅動、觸控板）→ 打開視覺效果。VM 階段的工作在實機上幾乎不用重做。
