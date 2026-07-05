---
title: "macOS APFS 卷結構與空間池：為什麼 df 的數字跟你想的不一樣"
date: 2026-07-05
slug: "macos-apfs-volume-structure"
description: "排查磁碟空間時需要理解 APFS 的 container/volume/volume group 三層架構和共用空間池機制。du、df、diskutil 三個工具看到的數字各自不同，原因在 APFS clone 和卷間共用。"
tags: ["macos", "apfs", "disk-space", "apple-silicon"]
---

macOS 的檔案系統從 HFS+ 換到 APFS 後，「磁碟空間」的概念從一對一（一個分割區對應一塊空間）變成多對一（多個卷共用一個空間池）。排查空間問題時，如果用 HFS+ 時代「每個分割區有自己的容量」的心智模型去讀 APFS 的數字，會得到矛盾的結果。

## 三層架構：Physical Store → Container → Volume

APFS 把一顆實體磁碟組織成三層：

**Physical Store** 是實體磁碟上的一個分割區。一台 Mac 的內建 SSD 通常有三個分割區：ISC（約 500MB，安全啟動用）、主分割區（幾乎佔滿整顆磁碟）、Recovery（約 5G）。主分割區裝載一個 APFS Container。

**Container**（APFS Container，磁碟空間管理單位，跟 [App Sandbox 的 Container](../macos_app_sandbox_container/) 是不同層級的概念）是空間管理的最上層單位。它從 Physical Store 拿到一塊空間，再分配給底下的 Volume。關鍵設計是：Container 裡的所有 Volume 共用同一個空間池，沒有預先劃分的配額。這代表任何一個 Volume 都能用到整個 Container 的剩餘空間，但也代表任何一個 Volume 膨脹都會壓縮其他 Volume 的可用空間。

```bash
# 查看 Container 的空間分配
diskutil apfs list
```

這台機器的 Container disk3 有 245.1GB，底下五個 Volume 共用這個池：

```text
Container disk3 (245.1 GB)
├── Macintosh HD    (System)   11.2 GB  — 唯讀系統卷，sealed
├── Preboot                    8.5 GB  — 開機前置資料 + Cryptex
├── Recovery                   2.2 GB  — 復原模式
├── Data                     207.7 GB  — 使用者資料，日常操作都在這
└── VM                         6.5 GB  — 虛擬記憶體 swap
                          剩餘  8.9 GB  — Container 未分配空間
```

**Volume** 是檔案系統的操作單位——目錄、檔案、權限都在這層。每個 Volume 有自己的 Role（System、Data、Preboot、Recovery、VM），決定它的用途和掛載方式。

## Volume Group：System 跟 Data 的綁定關係

macOS 把 System 卷和 Data 卷綁成一個 Volume Group。System 卷是唯讀的（sealed），放作業系統本體；Data 卷放使用者資料。開機時系統把兩者疊在一起，使用者看到的 `/` 是 System 卷的內容，`/Users`、`/Applications` 等路徑透過 firmlink 指向 Data 卷。

```bash
# 確認 Volume Group
diskutil info /System/Volumes/Data | grep "APFS Volume Group"
```

Volume Group UUID 在排查 Preboot 時很重要——Preboot 卷裡的開機資料是按 Volume Group UUID 組織的，一個 UUID 對應一套完整的開機資料。正常情況只有一個 UUID（見 [Preboot 卷](../macos_preboot_volume_check/)）。

## 空間池對排查的影響

共用空間池意味著不能把「各 Volume 的 Capacity Consumed 加起來」當成已用空間——因為 APFS 有 clone（多個檔案共用底層資料區塊）和 snapshot（時間點凍結），這些機制讓「屬於 Volume A 的區塊」和「屬於 Volume B 的區塊」之間有共用關係。

判斷「還剩多少可用空間」要看 Container 層的 Capacity Not Allocated，這是扣除所有 Volume 和 snapshot 的實際佔用後的真正剩餘：

```bash
# Container 層的未分配空間（真正的剩餘）
diskutil apfs list | grep -A5 "Container disk3" | grep "Capacity Not Allocated"
```

`df -h /` 或 `df -h /System/Volumes/Data` 顯示的 Available 也反映 Container 層的可用空間，但呈現方式不同——`df` 把整個 Container 的可用空間都算成 Data 卷的可用，因為 Data 卷可以用到池裡的任何剩餘空間。

## du、df、diskutil 數字不同的原因

三個工具看磁碟空間的視角不同，數字各有適用場景：

| 工具            | 看的是什麼                        | APFS clone 的處理     | 適用場景                     |
| --------------- | --------------------------------- | --------------------- | ---------------------------- |
| `du -skx`       | 逐檔累加實際佔用區塊              | 每個檔案各算一次      | 找哪個目錄/檔案佔最多        |
| `df -h`         | 檔案系統層的 used/available       | 反映 Container 層實態 | 快速看還剩多少               |
| `diskutil info` | Volume 或 Container 層的 metadata | 共用區塊只算一次      | 精確看某個 Volume 的實際佔用 |

差異在 APFS clone。Clone 讓多個檔案共用同一份底層資料區塊——修改其中一個時才複製被改的區塊（copy-on-write）。`du` 逐檔計算，每個 clone 各算一次；`diskutil` 看 Volume 層的實際區塊佔用，共用的只算一次。

這就是為什麼用 `du` 量 Preboot 卷會得到比 `diskutil info` 更大的數字（見 [Preboot 卷](../macos_preboot_volume_check/)）——Preboot 裡的 `os.dmg` 和 `os.clone.dmg` 是 APFS clone，`du` 把兩個檔案各算一次報約 11G，但 `diskutil` 看實際區塊佔用只有約 5.4G（單一 os.dmg 的大小），整個 Preboot 卷的 `diskutil` 佔用是 8.5G（含其他開機資料）。

**Sparse 檔案**是另一個差異來源。Sparse 檔案宣告了一個邏輯大小，但只有寫入過的區塊才真正佔磁碟。`ls -l` 和 `find -size` 看的是邏輯大小，`du` 看的是實際佔用。容器映像（OrbStack、VM 磁碟映像）常是 sparse 檔，邏輯大小可能是實際佔用的數十倍。排查空間大戶時一律用 `du`，不信 `ls` 的數字。

## 額外的 Container：iOS Simulator

iOS Simulator runtime 以 disk image（DMG）形式儲存在 Data 卷上，開機或使用時掛載成獨立的 APFS Container。這些 Container 出現在 `diskutil apfs list` 裡，看起來像是佔了額外的磁碟空間，但它們的 Physical Store 是 disk image 檔案——實際空間消耗在 Data 卷上，不是獨立的實體分割區。

```bash
# Simulator 的 disk image Container
diskutil list | grep "disk image"
```

這意味著刪除 Simulator runtime 回收的空間會反映在 Data 卷（和 Container 的未分配空間），而不是讓某個 Container 消失。詳見 [iOS Simulator runtime 架構](../macos_ios_simulator_runtime_architecture/)。
