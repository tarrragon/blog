---
title: "UEFI Boot Chain（開機鏈）"
date: 2026-07-01
description: "在 bootloader 選型（GRUB / EFISTUB / systemd-boot）卡住、或機器重開後找不到 kernel、需要理解韌體怎麼找到並載入系統時讀 — 韌體到 kernel 的交棒過程"
weight: 12
tags: ["dotfile", "linux", "boot", "uefi"]
---

UEFI 開機鏈是現代機器從通電到 kernel 跑起來的一段交棒過程：韌體 → 開機項 → bootloader → kernel。理解這條鏈，bootloader 選型與「重開機找不到系統」的故障才有判讀依據；kernel 旁通常還帶著 [initramfs](/linux/dotfile/knowledge-cards/initramfs/) 一起被載入。

## 概念位置

相關概念：[initramfs](/linux/dotfile/knowledge-cards/initramfs/)（bootloader 載入的對象之一）、[分區識別](/linux/dotfile/knowledge-cards/partition-identification/)。bootloader 選型的判讀，見 [Linux 安裝選項判讀](/linux/install/install-option-decisions/)。

UEFI 韌體開機時，要找到一個 EFI 執行檔來載入。它從兩個來源找：NVRAM（韌體用來存開機項的非揮發記憶體）裡登記的開機項，或 ESP（EFI System Partition，一個 FAT32 格式的分區）裡的標準路徑。找到的 EFI 執行檔可能是一個獨立的 bootloader，也可能直接是 kernel。

這對應兩種風格。EFISTUB 讓韌體直接載入 kernel、不經過獨立 bootloader，最精簡，但典型上依賴 NVRAM 裡的開機項。獨立 bootloader（GRUB、systemd-boot）則多一層：它有開機選單、能救援、還能裝到 ESP 的 fallback 路徑（`\EFI\BOOT\BOOT<ARCH>.EFI`，aarch64 是 `BOOTAA64.EFI`、x86_64 是 `BOOTX64.EFI`）。

fallback 路徑是這條鏈的保命機制。NVRAM 的開機項可能丟失——QEMU 系的虛擬機尤其容易——這時靠 NVRAM 開機項的 EFISTUB 會開不了機，而 fallback 路徑上有 bootloader 的機器，韌體仍找得到。這就是「VM 上偏好獨立 bootloader」的根據。

這條鏈預設 Secure Boot 關閉。Secure Boot 開啟時，韌體會拒載沒簽章的 EFI 執行檔（kernel 或 bootloader），這也是「重開後找不到 kernel」的一類成因——最小 VM 安裝通常把它關掉，但實體機若開著就要處理簽章。
