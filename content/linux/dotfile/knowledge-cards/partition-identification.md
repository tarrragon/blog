---
title: "分區識別（PARTUUID / FSUUID）"
date: 2026-07-01
description: "在 fstab 或 bootloader 設定要指定一個分區、不確定該用 PARTUUID、UUID 還是 /dev/sda1、或重格式化後系統開不了機時讀 — 分區的穩定識別方式"
weight: 13
tags: ["dotfile", "linux", "disk"]
---

分區識別是 `fstab`（開機時決定哪個分區掛到哪的設定檔）與 bootloader 指涉某個分區時用的名字，它的選擇決定一件事：重開機或重格式化後，系統還找不找得到自己的分區。

有三種識別方式，穩定性不同。PARTUUID 是寫在 GPT 分區表裡的 ID，綁在分區本身、跨重開機穩定，而且重新格式化檔案系統也不會變。FSUUID 是檔案系統 superblock（檔案系統開頭記錄自身中繼資料的區塊）裡的 UUID，綁在檔案系統上，所以一重新格式化就變，會讓引用它的 `fstab` 失效。kernel 名稱（`/dev/sda1`、`/dev/vda1`）則隨偵測順序浮動，多接一顆磁碟就可能對調，最不穩。`fstab` 還吃 `LABEL=` / `PARTLABEL=`（你自己給的標籤），穩定性看你維不維護那個標籤，跟前三種「系統生成」的識別不同層級，這裡不展開。

穩定性排序是 PARTUUID 優於 FSUUID 優於 kernel 名稱。在 GPT 磁碟上用 PARTUUID，得到「綁分區、重格不變」的最穩識別。這也是為什麼安裝程式問「device name scheme」時，GPT 磁碟選 PARTUUID。

理解這個差異，能解釋一類典型故障：重新格式化某個分區後機器開不了機，往往是因為 `fstab` 或 bootloader 用了 FSUUID，而格式化讓那個 UUID 變了。

相關概念：[UEFI 開機鏈](/linux/dotfile/knowledge-cards/uefi-boot-chain/)、[initramfs](/linux/dotfile/knowledge-cards/initramfs/)。安裝時的識別方式選擇，見 [Linux 安裝選項判讀](/linux/install/install-option-decisions/)。
