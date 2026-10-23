---
title: "macOS 移除多餘的 iOS Simulator Runtime"
date: 2026-07-05
slug: "macos_remove_redundant_ios_simulators"
description: "磁碟空間不足、發現裝了多版 iOS Simulator runtime 時的移除流程。透過 simctl 指令移除的步驟、順序、以及 Xcode GUI 的打包限制。"
tags: ["macos", "xcode", "ios-simulator", "disk-space", "troubleshooting"]
---

每組 [iOS Simulator runtime](../macos_ios_simulator_runtime_architecture/) 約 8G 到 16G：較早的版本由 Bundle DMG 與 Runtime DMG 兩份映像組成，較新的版本只有一份映像（`Cryptex/Images/bundle` 底下是 0B），實際大小以 `xcrun simctl runtime list -v` 的 Size 加上 bundle 目錄的 `du` 為準，裝了兩個版本就可能佔掉十幾到三十幾 GB。Flutter 和 Xcode 開發通常只需要最新版，舊版可以安全移除。移除的正確路徑是透過 Xcode 或 `simctl` 指令，不是手動刪除 `~/Library/Containers` 裡的檔案。

## 確認目前裝了幾組

```bash
xcrun simctl runtime list
```

輸出範例：

```text
== Disk Images ==
-- iOS --
iOS 18.2 (22C150) - 6286F286-FA4F-4877-AAEF-62A162C6A2C4 (Ready)
iOS 18.3.1 (22D8075) - 07012283-CA3D-4437-8A5F-89AE5346EEED (Ready)

Total Disk Images: 2 (16.2G)
```

兩組各自獨立，可以分開移除。

## 移除流程

先清掉綁在舊 runtime 上的模擬器裝置，再刪 runtime 本體。runtime 還裝著時，綁在它上面的裝置狀態是可用的，`xcrun simctl delete unavailable` 碰不到它們，所以要先用 `xcrun simctl list devices "<iOS 版本>"` 列出這些裝置，逐台用 UUID 刪除；`delete unavailable` 用來清掉 runtime 已經不存在的殘留裝置。

```bash
# 1. 關閉所有正在跑的模擬器
xcrun simctl shutdown all
killall Simulator 2>/dev/null

# 2. 列出綁在要刪除的 runtime 上的裝置，逐台用 UUID 刪除（引數換成要刪除的 iOS 版本與裝置 UUID）
xcrun simctl list devices "iOS 18.5"
xcrun simctl delete <裝置UDID>

# 3. 刪除指定 runtime（用 runtime list 裡的 identifier）
xcrun simctl runtime delete 6286F286-FA4F-4877-AAEF-62A162C6A2C4

# 4. 清掉 runtime 已不存在的殘留裝置，並確認
xcrun simctl delete unavailable
xcrun simctl runtime list
```

如果步驟 3 跑完沒報錯但 runtime 還在列表裡，通常是因為還有模擬器裝置綁在上面。回到步驟 1 和 2 重跑，或用 `xcrun simctl list devices` 查看哪些裝置還在用那個 runtime，手動刪掉它們：

```bash
# 列出所有模擬器裝置
xcrun simctl list devices

# 刪除特定裝置
xcrun simctl delete <裝置UDID>
```

## 為什麼不能手動刪檔案

一組 runtime 的資料散在多個位置（Runtime DMG、Bundle DMG、裝置資料、快取），各位置的關係和儲存機制見 [runtime 架構](../macos_ios_simulator_runtime_architecture/)。手動刪其中一處只會刪掉一部分，留下孤兒資料，讓 CoreSimulator 的索引跟實際檔案不一致。之後可能出現模擬器列表裡有裝置但開不了、或空間沒真正釋放的情況。`simctl runtime delete` 會清理 runtime 的映像與它在 CoreSimulator 裡的登記；模擬器裝置的資料存在 `~/Library/Developer/CoreSimulator/Devices`，要另外用 `simctl delete` 刪除。各類佔用的判斷與定期清理的流程，在 [開發機的定期空間清理](../macos_developer_periodic_cleanup/)。

## Xcode GUI 的限制

Xcode > Settings > Platforms 也可以管理 runtime，但它把相鄰版本打包成同一個下載單位顯示。例如 iOS 18.2 和 18.3.1 在介面上可能顯示為一個 8.71GB 的「iOS 18.2 + iOS 18.3.1 Simulator」項目，無法單獨刪除其中一個。這時用 `simctl` 指令是更精確的選擇。

## 刪完之後

重跑 [disk-report](../macos_disk_space_diagnosis/) 確認空間釋放。如果日後需要被刪除的版本，Xcode 會在建置或開啟模擬器時提示下載，或手動從 Settings > Platforms 下載。

```bash
# 驗證空間釋放
df -h /System/Volumes/Data
xcrun simctl runtime list
```
