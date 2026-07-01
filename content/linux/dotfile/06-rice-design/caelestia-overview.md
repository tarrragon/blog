---
title: "Caelestia 總覽：預組裝的 Hyprland 桌面 Shell"
date: 2026-06-29
description: "考慮用 Caelestia 取代手動拼裝 waybar+wofi+mako、或評估預組裝桌面 shell 的 trade-off 時回來讀"
weight: 3
tags: ["dotfile", "rice", "caelestia", "quickshell", "hyprland"]
---

Caelestia 是基於 Quickshell 框架的 Hyprland 桌面 shell。它把狀態列、啟動器、通知、鎖屏、桌布管理這些在平鋪式桌面上需要各自挑選和配置的元件，整合成一套設計一致的成品。本質上是一套高品質的 dotfiles/rice，不是一個穩定的桌面環境產品。

## Caelestia 提供的元件

手動拼裝的桌面需要 6-8 個獨立工具各自配置。Caelestia 把這些元件用 Quickshell 統一實作：

| 元件               | 手動拼裝的對應物        | Caelestia 的實作                                |
| ------------------ | ----------------------- | ----------------------------------------------- |
| 狀態列（Bar）      | Waybar                  | 工作區指示器、視窗標題、系統匣、時鐘            |
| 啟動器（Launcher） | Wofi / Rofi             | 模糊搜尋應用程式 + 桌布選擇介面                 |
| 通知               | Mako / Dunst            | 分組通知、過期控制                              |
| 鎖屏               | Hyprlock                | 模糊背景、可選指紋認證                          |
| OSD                | 自己用 script 拼        | 音量 / 亮度變更的螢幕顯示                       |
| 桌布管理           | Hyprpaper / Swww        | 每螢幕桌布、從桌布動態取色（Material Design 3） |
| Dashboard          | 無對應（自己拼 widget） | 媒體播放器（MPRIS）、CPU/GPU/RAM、天氣          |
| Sidebar            | 無對應                  | WiFi / 藍牙 / 暗色模式快速開關                  |
| Session menu       | 自己用 script 拼        | 登出 / 關機 / 重啟                              |
| Audio visualizer   | Cava（終端機）          | 桌面上的音訊視覺化                              |

## Quickshell 框架

Quickshell 是一個 Qt6/QML 的 shell framework，用來在 Wayland compositor 上渲染 UI 元件。它的角色是 Caelestia 跟 Hyprland 之間的中介層：

- 用 QML（Qt 的宣告式 UI 語言）描述介面元件
- 透過 `wlr-layer-shell` 協議把元件渲染成 Wayland layer surface（這是狀態列、啟動器能「黏在」螢幕邊緣的原因）
- 直接存取 Hyprland IPC，可以即時讀取工作區狀態、視窗資訊
- 配置檔修改後自動 reload，不需要重啟

跟其他桌面 shell 框架的差異主要在底層渲染引擎和配置語言。

## 跟 AGS / Eww 的比較

| 框架                       | 語言            | 渲染引擎 | 優勢                                                      | 劣勢                                                |
| -------------------------- | --------------- | -------- | --------------------------------------------------------- | --------------------------------------------------- |
| Quickshell（Caelestia 用） | QML（Qt6）      | Qt       | 即時視窗預覽、Hyprland IPC、auto-reload、豐富動畫         | Qt theming 複雜、positioning 不直覺、部分服務不完整 |
| AGS / Astal                | TypeScript / JS | GTK      | 完整的系統服務庫（Network、Bluetooth）、GObject、前端友善 | GTK 在 Wayland layer surface 上的限制               |
| Eww                        | Yuck（自定義）  | GTK/Rust | 輕量、配置語法簡單、生態成熟                              | 功能不如前兩者豐富、Yuck 是自定義 DSL 要額外學      |

選型判讀：想要開箱即用的華麗桌面 → Caelestia（Quickshell）。想要自己一個個拼、有前端經驗 → AGS。想要最簡單輕量 → Eww。想要完全控制每個細節 → 手動拼裝 waybar + wofi + mako。

## 跟手動拼裝的 Trade-off

**Caelestia 的優勢**是省去「挑工具 + 各自配置 + 統一視覺風格」的大量前期功夫。Material Design 3 的動態取色（從桌布自動提取配色方案套用到所有元件）是手動拼裝很難做到的。

**代價**是兩個：

第一，鎖定在 Caelestia 的設計決策裡。你可以調配色、改模組顯示、換桌布，但桌面的整體結構和行為邏輯是 Caelestia 決定的。想要「狀態列放底部 + 用不同的 launcher」這種結構性改動，比手動拼裝困難得多。

第二，穩定性風險。Caelestia 的 README 明確寫：「Configs, and internal tokens used in them, may be changed or removed without notice」。這表示一次更新可能靜默破壞你的自訂設定。這跟 Hyprland 本身的 breaking changes 疊加，等於你的桌面有兩層快速移動的依賴。

## 三個 GitHub Repo 的分工

| Repo                       | 角色                                        |
| -------------------------- | ------------------------------------------- |
| `caelestia-dots/caelestia` | 主 dotfiles — Hyprland config、應用程式配置 |
| `caelestia-dots/shell`     | UI 層 — Quickshell/QML 實作的所有桌面元件   |
| `caelestia-dots/cli`       | CLI 工具 — 安裝、主題切換、截圖、錄影等指令 |

完整安裝（`caelestia install`）會同時部署三者。也可以只裝 shell（`caelestia-shell` AUR package），保留自己的 Hyprland config 和應用程式設定。

## 定位認知

Caelestia 的本質是一套社群維護的 rice dotfiles，不是有 release cycle 和 backward compatibility 承諾的軟體產品。用它的心態應該接近「fork 別人的 dotfiles 來改」而不是「安裝一個桌面環境」。這個定位決定了它適合什麼人：享受折騰和客製化的人會從中得到很好的起點，想要穩定日用的人應該考慮 GNOME 或 KDE Plasma。
