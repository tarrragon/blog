---
title: "initramfs"
date: 2026-07-01
description: "看到 ESP 大小要算進 initramfs、或開機卡在掛載 root 之前、不知道 initramfs 是什麼時讀 — 開機初期掛真 root 之前的臨時根檔系統"
weight: 11
tags: ["dotfile", "linux", "boot"]
---

initramfs（initial RAM filesystem）是 kernel 開機初期、在真正的 root 檔案系統被掛起來之前，載入記憶體的一個小型臨時根檔系統。

它的責任是「把掛載真 root 所需的東西先備齊」。kernel 本身不內建所有硬體與檔案系統的驅動，當 root 位在一個需要額外驅動才讀得到的裝置上——LVM 邏輯卷、LUKS 加密卷、特殊磁碟控制器——kernel 沒辦法直接掛它。initramfs 提供一個臨時環境，把這些驅動與工具載進來、把真 root 掛起來，然後把控制權交給真 root 上的 init。

因為它要跟 kernel 一起被 bootloader 載入，所以它跟 kernel 放在同一個地方——[UEFI 開機鏈](/dotfile/knowledge-cards/uefi-boot-chain/)裡的 ESP，或獨立的 `/boot`。這也是為什麼估 ESP 大小時要把它算進去：一個 kernel 加上它的 initramfs（含 fallback 版本）大約一兩百 MB。

生成工具依發行版而異：Arch 用 `mkinitcpio`、Fedora 用 `dracut`。換了 kernel 或改了開機需要的驅動，要重新生成 initramfs，否則新 kernel 可能掛不起 root。

相關概念：[UEFI 開機鏈](/dotfile/knowledge-cards/uefi-boot-chain/)、[分區識別](/dotfile/knowledge-cards/partition-identification/)。安裝時 ESP 大小怎麼估，見 [Linux 安裝選項判讀](/dotfile/linux-install/install-option-decisions/)。
