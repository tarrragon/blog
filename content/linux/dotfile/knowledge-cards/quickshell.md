---
title: "Quickshell（QML 桌面 shell runtime）"
date: 2026-07-03
description: "rice 模組反覆出現 Quickshell、想確認它跟 Caelestia 誰是框架誰是成品、為什麼裝它要 200 多 MB、pgrep 為什麼找不到它時讀"
weight: 17
tags: ["dotfile", "linux", "quickshell", "qml", "rice", "knowledge-cards"]
---

Quickshell 是建在 Qt6/QML 上的桌面 shell runtime：一個在 Wayland [compositor](/linux/dotfile/knowledge-cards/compositor/) 之上渲染桌面 UI 元件（狀態列、啟動器、通知、鎖屏）的執行框架。它自己不是一套桌面——它提供 QML 執行環境跟一組系統整合 API（Hyprland IPC、視窗預覽、auto-reload），桌面長什麼樣由使用者（或像 Caelestia 這樣的專案）用 QML 寫出來。

## 概念位置

相關概念：[Compositor](/linux/dotfile/knowledge-cards/compositor/)（Quickshell 在其上渲染、由它持有畫面）、[Session Lock](/linux/dotfile/knowledge-cards/session-lock/)（Quickshell 持鎖死掉時的失效保護）、[AUR](/linux/dotfile/knowledge-cards/aur/)（`quickshell-git` 的來源與 `-git` 依賴衝突）、[Rice](/linux/dotfile/knowledge-cards/rice/)（它服務的桌面客製文化）。

跟 Caelestia 的關係是「runtime 與成品」：[Caelestia](/linux/dotfile/06-rice-design/caelestia-overview/) 是一套用 Quickshell 寫成的完整桌面 shell（QML 元件 + 配置 + CLI），Quickshell 是跑它的引擎。這個分工解釋了兩件教材裡的實務約束：其一，Caelestia 要求 `quickshell-git`（[AUR](/linux/dotfile/knowledge-cards/aur/) 的開發版套件）——穩定版缺它需要的 API，裝穩定版 shell 起不來；其二，Quickshell 目前只有 Arch 生態打包，桌面層清單因此是平台專屬的維護對象（見[平台差異地圖](/linux/install/platform-divergence-map/)）。

它的資源足跡是「整合式 shell vs 手動拼裝」選型的主要成本項。`quickshell` 套件本身約 213 MB，Qt6 函式庫（`qt6-declarative`、`qt6-base`）還是額外相依；對照手動拼裝的 waybar + wofi + mako 合計不到 5 MB。這筆成本買到的是單一 runtime 內風格一致、能共享狀態與動畫的整套 UI——取捨的完整推導見[整合式 shell 與手動拼裝的選擇](/linux/dotfile/06-rice-design/integrated-shell-vs-manual-assembly/)。

除錯時它有兩個判讀陷阱，都源自「一個 runtime 畫整個桌面」的架構：

- **行程名是 `qs` 不是 `quickshell`**：可執行檔叫 `quickshell`，但透過 `/usr/bin/qs` 這個 symlink 啟動時行程表裡的 comm 是 `qs`——`pgrep quickshell` 跟 `pgrep caelestia` 都落空，容易誤判成掛了。判程式活著的通用紀律見[程序、服務與狀態怎麼判](/linux/debug/process-service-state-diagnosis/)。
- **畫得出來不等於還活著**：QML scene 裡某個物件初始化失敗變 null 時，進程還在、bar 還停在最後一幀，但互動接線已死。這類「進程活著、內部子系統死了」的故障與復原見[常見故障場景與恢復操作](/linux/dotfile/07-desktop-maintenance/common-failures-recovery/)。

同源架構也放大了故障的連帶範圍：Caelestia 的鎖屏由 Quickshell 主程式畫，主程式死掉時 compositor 依 ext-session-lock 維持鎖定進入失效保護——狀態列、通知、鎖屏一起消失，復原路徑見 [Session Lock](/linux/dotfile/knowledge-cards/session-lock/)。
