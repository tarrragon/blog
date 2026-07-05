---
title: "macOS Preboot 卷：從 Intel 的 1G 到 Apple Silicon 的 8G"
date: 2026-07-05
slug: "macos-preboot-volume-check"
description: "排查磁碟空間時需要判斷 Preboot 卷的大小是否合理。Intel 時代的 1-2G 經驗不適用於 Apple Silicon，理解 Cryptex 機制後才能做正確判斷。"
tags: ["macos", "disk-space", "apfs", "apple-silicon"]
---

磁碟空間排查到 APFS container 層級時，`diskutil apfs list` 會列出每個卷的佔用。Preboot 卷在 Apple Silicon Mac 上通常顯示 8-10G，如果用 Intel Mac 時代 1-2G 的經驗來判讀，會誤以為有問題。這個差異來自 Apple Silicon 引入的 Cryptex 機制，理解它的運作方式後，判斷 Preboot 的大小是否合理就不需要查表。

## Preboot 在開機流程中的角色

Preboot 是 [APFS container](../macos_apfs_volume_structure/) 裡的五個卷之一，專門存放開機前置資料——開機載入器、核心快取、安全驗證票證。這些東西必須在 Data 卷解鎖之前就能讀取，所以放在獨立的卷裡。所有卷共用同一個空間池，Preboot 佔多少 Data 就少多少。

## Intel Mac 的 Preboot：簡單的開機載入器

在 Intel Mac 上，Preboot 的內容很單純：一組 `boot.efi`（EFI 開機載入器）、少量開機設定、以及 FileVault 解鎖介面的資源。這些加起來通常只有 1-2G，而且幾乎不會變動——裝完系統後大小就固定了，不會隨使用時間膨脹。

這個時期建立的經驗是：Preboot 應該很小，超過幾 GB 就是有問題。

## Apple Silicon 的 Preboot：Cryptex 改變了容量結構

Apple Silicon Mac 從 macOS 13 開始引入 Cryptex（Cryptographically Sealed Extension），Preboot 的內容和大小因此完全改變。

Cryptex 解決的問題是安全更新的部署速度。在 Cryptex 之前，修一個 Safari 漏洞需要推一整版 macOS 更新——整個系統卷要重新驗證、重新封印。Cryptex 把 Safari 和系統安全元件從系統卷抽出來，封裝成獨立的簽章 DMG，放在 Preboot 卷裡。開機時系統把 Cryptex DMG 掛載、疊加到系統卷上層，效果等同於系統卷的一部分，但更新時只要替換這個 DMG，不動系統卷本體。

這個設計的代價是 Preboot 的體積。一組 Cryptex 的 `os.dmg` 約 5.4G，是 Preboot 佔用的主力。加上 `restore` 開機復原資料（約 800M-1G）、各機型的 `kernelcache`（每個約 30M，十幾個機型合計數百 MB）、以及 `boot` 載入器（約 50M），Apple Silicon 的 Preboot 基本盤就在 6-8G 左右。

### restore-staged：更新機制的暫存區

Preboot 裡還有一個 `restore-staged` 目錄，是系統更新機制的暫存區。macOS 會在背景下載更新資料（韌體映像、加密的 DMG、核心快取），先 staging 到這裡，等使用者同意安裝或自動維護窗口到來時才套用。

這個目錄的大小在 0-2G 之間浮動，取決於是否有待套用的更新。它的內容不一定對應「當前版本的下一版」——這次實測中，`restore-staged` 裡的 `RestoreVersion.plist` 顯示的版本號是 26.3.1（這是 plist 內部的 restore 版本號，跟 macOS 行銷版本號不同），而當前系統是 macOS 15.3.1。這表示 staging 的資料可能是 Apple 為未來升級預先準備的，跟「有待套用的安全更新」是不同的 staging 類型。

## du 跟 diskutil 數字不一致的原因

用 `du` 量 Preboot 會得到比 `diskutil info` 更大的數字（這次實測：`du` 報 13G，`diskutil` 報 8.5G）。原因是 Preboot 裡的 `os.dmg` 和 `os.clone.dmg` 是 APFS clone，`du` 各算一次、`diskutil` 共用區塊只算一次。du 和 diskutil 的差異機制見 [APFS 卷結構](../macos_apfs_volume_structure/)。

判斷 Preboot 佔用時用 `diskutil info` 的 Volume Used Space：

```bash
diskutil info /System/Volumes/Preboot | grep "Volume Used Space"
```

## 正常的 Preboot 結構

一台 Apple Silicon + macOS 14-16 的機器，Preboot 的典型內部結構：

```text
/System/Volumes/Preboot/<Volume-Group-UUID>/
├── cryptex1/current/       # Cryptex 本體（5-7G）
│   ├── os.dmg              # 系統安全元件
│   ├── os.clone.dmg        # APFS clone，不額外佔空間
│   └── app.dmg             # App 層元件（~20M）
├── restore-staged/         # 更新暫存（0-2G，浮動）
├── restore/                # 復原用開機資料（~800M）
├── boot/                   # 開機載入器（~50M）
└── var/, usr/, ...         # 開機輔助資料（~25M）
```

Volume Group UUID 正常情況只有一個，對應當前系統的 Data 卷。確認方式：

```bash
# Preboot 裡的 UUID
ls /System/Volumes/Preboot/ | grep -E '^[0-9A-F]{8}-'

# 當前系統的 Volume Group UUID
diskutil info /System/Volumes/Data | grep "APFS Volume Group"
```

## 什麼情況才真的有問題

基於上面的機制，判讀 Preboot 大小是否合理的依據是結構性指標，不是絕對大小。

**多個 Volume Group UUID**：Preboot 裡出現多個 UUID 目錄，表示曾有過多重 macOS 安裝。每組 UUID 各帶一份完整的 Cryptex 和開機資料，所以 Preboot 會翻倍。只有對應當前 Data 卷 UUID 的那個是必要的，其他是舊安裝殘留。這是 Preboot 超過 15G 最常見的原因。

**restore-staged 異常堆積**：超過 3G 且日期距今超過一個月，可能是下載了更新但套用失敗或被中斷。正常的處理方式是在系統設定裡完成或重新下載更新，更新完成後系統會自動清理這個目錄。

**Cryptex 沒有成功替換**：`cryptex1/` 目錄裡除了 `current` 還有其他子目錄，可能是舊版 Cryptex 沒被正常替換。安裝最新的安全更新通常能解決。

這些情況都不應該用手動刪檔的方式處理。Preboot 是安全啟動鏈的一部分，APFS 的 snapshot 和 clone 關係讓手動刪除可能影響到看不見的依賴。正確路徑是透過系統更新、Recovery 模式重裝、或 Apple Support 來處理。

## disk-report 的 Preboot 段落

這些判讀邏輯已整合進 [disk-report](https://github.com/tarrragon/scripts) 腳本的 `--preboot` 模式，用 `diskutil info`（不是 `du`）取實際佔用，計算 Volume Group UUID 數量，檢查 `restore-staged` 的大小和日期，輸出一行結論。完整磁碟診斷時（`disk-report` 不帶參數）會自動包含這個段落。
