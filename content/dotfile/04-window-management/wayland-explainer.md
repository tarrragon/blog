---
title: "Wayland 顯示協議：為什麼 Hyprland 不跑在 X11 上"
date: 2026-06-29
description: "想理解 Hyprland 底層的圖形架構、Wayland 跟 X11 的差異、XWayland 相容層、以及 2026 年 Wayland 已經是主流這件事時回來讀"
weight: 1
tags: ["dotfile", "wayland", "x11", "linux"]
---

Wayland 是 Linux 圖形系統的顯示協議，定義了應用程式怎麼跟負責畫面合成的 compositor 溝通。Hyprland、Sway 這些 tiling WM 都是 Wayland compositor——理解 Wayland 的架構，才能理解這些工具為什麼存在、能做什麼、不能做什麼。

## Wayland 是協議，不是軟體

一個常見的誤解是把 Wayland 當成「一個程式」。Wayland 是一份協議規格（protocol specification），描述了 client（應用程式）和 compositor（負責合成畫面的東西）之間怎麼傳遞 buffer、怎麼處理輸入事件。

每個 Wayland compositor 同時扮演三個角色：display server（管理顯示輸出）、window manager（管理視窗排列）、compositor（合成最終畫面）。X11 的世界裡這三個角色是分開的，Wayland 把它們統一成一個程式。

這就是為什麼你會看到「Hyprland 是 Wayland compositor」這個說法——它不只是一個視窗管理器，它同時是整個圖形系統的核心。

## X11 vs Wayland 架構差異

### X11 的三角架構（1984 年設計）

```text
應用程式 ──→ X Server（中央仲介）──→ Compositor ──→ 螢幕
             ↑                         ↑
             └── 輸入事件 ──────────────┘
```

X Server 是一個龐大的中央仲介，負責接收所有應用程式的繪圖指令、管理輸入事件、再把畫面交給 compositor 做最終合成。Compositing 是後來才加上去的（Compiz、picom 這些都是外掛的 compositor），不是 X11 原始設計的一部分。

### Wayland 的直接模型（2008 年設計）

```text
應用程式 ──→ Compositor（= display server + window manager）──→ 螢幕
             ↑
             └── 輸入事件
```

應用程式用 OpenGL/Vulkan 自己渲染畫面到 buffer，然後把 buffer 直接交給 compositor。沒有中間人。compositor 收到所有 client 的 buffer 後合成最終畫面輸出到螢幕。

這個架構上的差異帶來三個實際影響：效能、安全、screen tearing。

## 安全性

X11 的安全模型有一個根本性的設計缺陷：任何連到同一個 X Server 的 client，都能監聽其他 client 的鍵盤輸入、擷取其他視窗的畫面、甚至注入假的輸入事件。這代表一個惡意程式可以輕易做到 keylogging——記錄你在其他視窗打的所有字，包括密碼。

Wayland 從協議層就隔離了 client 之間的存取。每個應用程式只看得到自己的 buffer，無法存取其他視窗的內容或輸入。要做 screen capture 或 screen sharing，必須透過 xdg-desktop-portal 這個受控的中介機制，使用者會看到明確的授權提示。

對 tiling WM 的使用者來說，這個安全差異特別有意義：平鋪式桌面通常同時開大量終端機視窗（有些跑 SSH、有些在 sudo 操作），X11 下任何一個視窗裡的惡意程式都能讀到其他視窗的鍵盤輸入。Wayland 阻斷了這條攻擊路徑。

## 效能與 Screen Tearing

X11 的渲染路徑有多餘的記憶體複製——應用程式把繪圖指令送給 X Server，X Server 渲染後再交給 compositor，compositor 再合成。Wayland 省掉了中間那一步：應用程式直接渲染到 buffer、直接交給 compositor，記憶體複製更少。

Screen tearing（畫面撕裂）在 X11 上是長年的老問題——需要 compositor + vsync 的各種 workaround。Wayland 在協議層就處理了 frame presentation 的時機，compositor 控制什麼時候把合成好的畫面送到螢幕，原生消除 tearing。這也是為什麼 Hyprland 的動畫能跑得流暢——直接 rendering + 原生 vsync 的組合，在 X11 上需要大量額外配置才能接近的效果。

## XWayland：X11 相容層

很多應用程式仍然只支援 X11 協議。XWayland 是一個 X11 server，但它本身作為一個 Wayland client 運行——X11 應用程式連到 XWayland，以為自己在跟正常的 X Server 溝通；XWayland 把 X11 協議翻譯成 Wayland 協議，把 buffer 交給 compositor。

多數 Wayland compositor（包括 Hyprland）預設啟用 XWayland，X11 應用程式不需要任何設定就能運行。

### 需要 XWayland 的常見應用

- 舊版 Electron 應用（新版可用 `--ozone-platform=wayland` 旗標切換到 Wayland 原生）
- Java 應用程式（NetBeans 等）
- 舊的 GTK2 應用程式
- 部分 Wine/Proton 遊戲（但 XWayland 下的遊戲效能已經相當好）
- Emacs（內部不是真正的 GTK 應用）

### XWayland 的已知問題

最大的實務痛點是 **HiDPI 非整數縮放**。在 150%、125% 等非整數 scale 下，XWayland 應用程式可能出現模糊渲染，因為 XWayland 不支援 fractional scaling 協議。整數縮放（100%、200%）則沒有問題。

## 關鍵 Wayland 協議

### wlr-layer-shell

Layer-shell 定義了 client 可以在螢幕的哪個「層」上建立畫面——background（最底）、bottom、top、overlay（最頂）。Status bar（waybar）、notification daemon（mako）、launcher（wofi）、wallpaper（hyprpaper）、lock screen（hyprlock）都透過 layer-shell 來佔據螢幕空間。

沒有 layer-shell 支援的 compositor，這些桌面元件就無法運作。這也是為什麼模組六（Rice 設計）的所有工具都只能在支援 layer-shell 的 Wayland compositor 上跑——它是可組裝式桌面的基礎設施。

### xdg-desktop-portal

Portal 是一個 D-Bus 介面，讓被隔離的 Wayland 應用程式可以請求特權操作：screen sharing、檔案對話框、螢幕截圖。每個 compositor 提供自己的 portal backend：

- Hyprland：`xdg-desktop-portal-hyprland`
- GNOME：`xdg-desktop-portal-gnome`
- KDE：`xdg-desktop-portal-kde`
- Sway/wlroots 系：`xdg-desktop-portal-wlr`

Screen sharing 的完整鏈路是：`PipeWire` + `xdg-desktop-portal-hyprland`。OBS 的 PipeWire source、瀏覽器的畫面分享，都走這條路。

## wlroots 與 Hyprland 的關係

wlroots 是一個模組化的 C library，提供 Wayland compositor 的共用基礎建設——輸入處理、輸出管理、協議實作。Sway、river、wayfire 這些 compositor 都基於 wlroots 開發，共享同一套底層程式碼。

Hyprland 最初也基於 wlroots，但後來 fork 出去自己維護底層。這讓 Hyprland 可以更快地加入新功能（動畫、模糊、漸層邊框），不需要等 wlroots 上游審核。代價是 Hyprland 的更新不再跟 wlroots 生態同步，偶爾會有相容性差異。

## 2026 年的 Wayland 採用現況

Wayland 在 2026 年已經從「取代 X11 的方向」變成「Linux 桌面的預設」：

| 桌面環境 / 發行版 | 狀態                                                              |
| ----------------- | ----------------------------------------------------------------- |
| GNOME             | GNOME 49（2025）放棄 X11 session，計劃在 GNOME 50 永久移除        |
| KDE Plasma        | Plasma 6.0 起預設 Wayland，6.8（2026 末）將 Wayland-only          |
| Fedora            | Fedora 43 完全移除 X11                                            |
| Ubuntu            | Ubuntu 25.10 不再提供 X11 session                                 |
| 整體採用率        | 2025 年報告顯示 Wayland 佔 Linux 桌面環境 52.7%                   |
| NVIDIA 驅動       | driver 555+ 支援 GBM，590 系列（2025）修復了多數 HDR 和多螢幕問題 |

X11 上的老牌 tiling WM（i3、bspwm、dwm）仍然活躍，但不再是新專案的主流方向。新的 tiling WM 幾乎都選擇 Wayland 作為基礎。

## X11 仍有優勢的場景

Wayland 並非在所有面向都超越 X11：

- **SSH X forwarding**：X11 原生支援透過網路轉送 GUI 視窗（`ssh -X`）。Wayland 沒有對等機制，替代方案是 `waypipe`，但不是 drop-in replacement
- **GUI 自動化**：`xdotool`、`wmctrl` 這類工具在 X11 上可以操控任何視窗。Wayland 下需要 compositor 特定的工具（Hyprland 用 `hyprctl`），跨 compositor 的通用方案還不成熟
- **VNC / 遠端桌面**：X11 的網路透明性讓遠端桌面相對簡單。Wayland 需要 PipeWire + portal，設定複雜度更高
- **Color management**：專業色彩工作流（ICC profile 管理）在部分 Wayland compositor 上仍需手動配置

這些場景如果是你的核心需求，目前 X11（或 X11-based 的 i3/sway 的 X11 版本）可能仍是更務實的選擇。

## 為什麼 Tiling WM 使用者該關心 Wayland

平鋪式桌面是「自己從元件組裝桌面」的工作流。Wayland 的幾個特性讓這件事變得更好：

**layer-shell** 給了 status bar、launcher、notification daemon 一個標準化的方式來佔據螢幕空間，不再需要各種 hack 讓這些元件「浮在視窗上面又不被平鋪規則管到」。

**安全隔離**在多終端機場景特別有價值——你可能同時開著 SSH session、密碼管理器、sudo 操作，Wayland 確保任何一個視窗裡的程式都無法偷看其他視窗的鍵盤輸入。

**直接 rendering** 讓 Hyprland 能做到流暢的視窗動畫和即時模糊，這在 X11 上需要大量額外的 compositor 配置（picom + 各種 backend 選擇 + vsync 調校）才能接近。

從實務角度看：如果你在 2026 年開始接觸 Linux tiling WM，選 Wayland-based 的工具（Hyprland、Sway）是順流而行。X11 不會立刻消失，但新功能、新工具、社群活力都在 Wayland 這一邊。
