---
title: "Compositor（合成器）"
date: 2026-07-02
description: "教材反覆出現 compositor / 合成器、想確認它到底負責什麼、跟 window manager 和桌面環境差在哪時讀 — Wayland 下把畫面合成與視窗管理合一的核心程式"
weight: 10
tags: ["dotfile", "linux", "wayland", "compositor", "hyprland"]
---

Compositor（合成器）是 Wayland 下負責把各個應用視窗的畫面合成到螢幕、同時管理視窗位置與輸入的核心程式。它一個角色承擔了舊 X11 世界裡分給多個程式的責任——畫面合成、視窗管理、輸入處理，在 Wayland 架構裡合在同一個程式。[Hyprland](/linux/dotfile/05-hyprland-config/) 就是一個 Wayland compositor。

跟 X11 的分工對照能看清它的定位。X11 時代，X server 負責畫面、一個獨立的 window manager 負責視窗排列，兩者透過協定溝通；Wayland 取消這個分家，compositor 直接兼任兩者。所以在 Wayland 語境裡，「compositor」和「window manager」常指同一個東西——Hyprland 既是 compositor 也是 tiling window manager。

它跟桌面環境（desktop environment）是不同層次。桌面環境（GNOME、KDE）是一整套元件（面板、設定、通知、檔案管理），其中內含一個 compositor；而 Hyprland 這類「只有 compositor」的方案不含那圈桌面服務，面板、啟動器、鎖屏都要另外自己接。這條「整合度 vs 自己組裝」的軸線，是[桌面環境選型](/linux/tools/gui/desktop-environment-selection/)的主題。

compositor 在故障排除中是一個關鍵的責任邊界，因為多個系統狀態由它持有、而非別的層：

- **它握著 DRM master**：直接畫到顯示裝置的獨佔權由 compositor 持有，這是為什麼 compositor 的**預設（DRM）backend** 要從實體圖形 VT 起、從 SSH pty 起會失敗（SSH 連線裡沒有那個 [seat](/linux/dotfile/knowledge-cards/logind-session-seat/) 與 DRM 資源），也是為什麼它跟同樣要畫到 DRM 的 [kmscon 之類 userspace console](/linux/dotfile/knowledge-cards/tty/) 會相衝。精確說是「預設 backend 需要圖形 VT」、不是「compositor 一定起不來」——多數 compositor 有 headless backend（`WLR_BACKENDS=headless`）不吃 DRM master、供 CI／雲端／自動化測試從無螢幕環境起，[遠端連線與終端機問題](/linux/debug/ssh-and-terminal-troubleshooting/)有這條的實作。
- **它持有 session lock 狀態**：Wayland 的 `ext-session-lock` 鎖是 compositor 層的狀態、跟 logind 獨立，殺掉鎖屏程式 compositor 仍保持鎖定——詳見 [Session Lock](/linux/dotfile/knowledge-cards/session-lock/)。
- **它掛了、桌面才真的黑**：反過來說，只要 kernel 還活著、compositor 以外的東西壞了，[TTY](/linux/dotfile/knowledge-cards/tty/) 仍能登入操作。判斷「畫面黑」是 compositor 掛了、還是沒 getty、還是顯示輸出沒接，是桌面故障排除的第一個分岔。

相關概念：[TTY](/linux/dotfile/knowledge-cards/tty/)（不依賴 compositor 的救生通道）、[Session Lock](/linux/dotfile/knowledge-cards/session-lock/)（compositor 持有的鎖定狀態）、[Rice](/linux/dotfile/knowledge-cards/rice/)（在 compositor 上做視覺客製）、[Quickshell](/linux/dotfile/knowledge-cards/quickshell/)（在 compositor 之上渲染桌面 UI 的 runtime）。
