---
title: "TTY"
date: 2026-06-30
description: "恢復操作提到切 TTY 但不知道 TTY 是什麼時讀 — Linux 核心直接提供的純文字終端機介面"
weight: 10
tags: ["dotfile", "linux", "tty"]
---

TTY（TeleTYpewriter）是 Linux 核心直接提供的純文字終端機介面，獨立於任何桌面環境或圖形介面。

名稱來自早期電腦透過電報打字機（teletypewriter）做輸入輸出的歷史。現代 Linux 的 TTY 是 virtual console——核心在記憶體中模擬的文字終端機，不需要實體硬體。

systemd 預設配置下有 6 個 virtual console（TTY1-TTY6）。Wayland compositor（如 [Hyprland](/linux/dotfile/05-hyprland-config/)）通常佔用 TTY1 顯示圖形桌面，TTY2-TTY6 保持為純文字介面可用。

切換方式：`Ctrl+Alt+F2`（切到 TTY2）到 `Ctrl+Alt+F6`（切到 TTY6）。`Ctrl+Alt+F1` 切回圖形桌面（TTY1）。

TTY 在桌面故障排除中的價值在於它**不依賴 compositor**。Compositor 掛了、GPU driver 出問題導致畫面凍結——只要 kernel 還活著，TTY 就能登入操作。這是 Linux 桌面環境「掛了不等於崩潰」的關鍵機制，詳見[桌面環境維護與故障排除](/linux/dotfile/07-desktop-maintenance/)。

相關概念：[Rice](/linux/dotfile/knowledge-cards/rice/)（桌面客製化）、[GNU Stow](/linux/dotfile/knowledge-cards/gnu-stow/)（dotfile 管理）。
