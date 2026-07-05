---
title: "iOS Simulator Runtime 架構：為什麼一組要 16G"
date: 2026-07-05
slug: "macos-ios-simulator-runtime-architecture"
description: "iOS Simulator runtime 每組約 16G（Bundle 8G + Runtime 8G），以 disk image 形式儲存在 Data 卷上、掛載成獨立 APFS Container。理解這個架構後才能判斷裝幾組合理、刪除回收多少空間。"
tags: ["macos", "xcode", "ios-simulator", "disk-space", "apple-silicon"]
---

iOS Simulator 讓開發者在 Mac 上跑 iOS App 而不需要實體裝置。每個 Simulator runtime 對應一個 iOS 版本——裝了 iOS 18.2 和 18.3.1 兩組 runtime，就能在兩個版本上測試。每組 runtime 約 16G，是 Mac 上最大的單一空間消耗者之一，但這個數字在日常開發中不容易察覺，直到磁碟空間不夠才會被發現。

## 一組 Runtime 的組成

每組 iOS Simulator runtime 由兩個 DMG（disk image）組成：

**Bundle DMG**（約 8G）：包含 Simulator 的 Cryptex 安全元件和啟動資料。儲存在 `/Library/Developer/CoreSimulator/Cryptex/Images/bundle/` 下。

**Runtime DMG**（約 8G）：包含完整的 iOS 檔案系統——所有系統框架、內建 App、字型、語言資源。儲存在 `/System/Library/AssetsV2/com_apple_MobileAsset_iOSSimulatorRuntime/` 下。

兩個 DMG 合起來約 16G，是一組 runtime 的完整大小。

```bash
# 查看已安裝的 runtime 和總大小
xcrun simctl runtime list
```

```text
== Disk Images ==
-- iOS --
iOS 18.3.1 (22D8075) - 07012283-CA3D-4437-8A5F-89AE5346EEED (Ready)

Total Disk Images: 1 (8.1G)
```

`simctl runtime list` 報的 8.1G 是 Runtime DMG 的大小，沒有包含 Bundle DMG。完整佔用要兩者相加。

## DMG 掛載成獨立 APFS Container

使用 Simulator 時，macOS 把這兩個 DMG 掛載成獨立的 APFS Container。`diskutil list` 會看到它們以 `(disk image)` 標示：

```text
/dev/disk4 (disk image):    →  iOS 18.3.1 Simulator Bundle    9.0 GB
/dev/disk6 (disk image):    →  iOS 18.3.1 Simulator           19.8 GB
```

這些 Container 的 Physical Store 是 DMG 檔案本身——實際的磁碟空間消耗在主 Container（disk3）的 Data 卷上。刪除 runtime 回收的空間會反映在 Data 卷的可用空間，而不是讓這些 disk image Container 消失（它們會自動卸載）。

Container 顯示的大小（9.0G、19.8G）是 DMG 內部的邏輯容量，比 DMG 檔案的實際磁碟佔用（各約 8G）略大，因為檔案系統有自己的 metadata 開銷。判斷空間佔用時看 DMG 檔案的 `du` 值，不看 Container 的 Size。

## 為什麼每組要 16G

iOS Simulator 是完整的 iOS 使用者空間環境——App 在 Simulator 上跑時，呼叫的是真正的 iOS 系統框架（UIKit、Foundation、SwiftUI），這些框架需要完整打包在 runtime 裡。Simulator 跑的是 x86_64 或 arm64 原生碼（Apple Silicon Mac 上是 arm64），所以框架二進位跟實體裝置上的不同，必須另外編譯一套。

16G 裡大約的分佈：

- 系統框架和 dyld shared cache：佔最大宗，包含所有 iOS 框架的預連結版本
- 內建 App（Safari、設定、照片等）：Simulator 需要完整的系統環境
- 多語言資源：字型、語言包、輔助使用資源
- Cryptex 安全元件：跟 macOS 的 Cryptex 機制類似（見 [Preboot 卷](../macos_preboot_volume_check/)），讓 Simulator 的安全元件可以獨立更新

相鄰版本（如 18.2 和 18.3.1）共用大部分內容，但 Apple 目前不做跨版本 delta 壓縮——每組 runtime 是完整獨立的。這是為什麼裝兩組就是 32G、三組就是 48G，線性增長。

## 裝幾組合理

判準是開發工作實際需要測試的 iOS 版本數量：

**一組（最新版）**：適合多數開發者。Flutter 和 SwiftUI 開發通常只需要在最新 iOS 上測試，舊版相容性問題靠 API availability check 處理，不需要實際跑 Simulator。

**兩組（最新 + 上一個大版本）**：App 的 deployment target 設在上一個大版本（例如 iOS 17）時，需要在該版本上跑 UI 測試確認佈局和行為。

**三組以上**：企業 App 支援更舊的 iOS 版本，或需要測試跨版本升級行為。這種情況下空間成本是已知的取捨。

不確定時，先裝最新版，需要舊版時再下載——Xcode 會在建置或開啟 Simulator 時提示，下載約需 30 分鐘（視網路速度）。

## 跟磁碟空間排查的關係

Simulator runtime 的空間佔用有兩個特徵讓它在排查時容易被忽略：

1. **DMG 檔案不在家目錄下**：`du -shx ~/*` 不會掃到它們，因為 DMG 儲存在 `/System/Library/AssetsV2/` 和 `/Library/Developer/CoreSimulator/`。家目錄層的排查會完全漏掉這塊。

2. **掛載後的 Container 看起來像獨立磁碟**：`diskutil apfs list` 列出的 Simulator Container 容易被誤認為是獨立的磁碟空間佔用，但它們的 Physical Store 是 Data 卷上的 DMG 檔案。理解 APFS 的 Container/Physical Store 關係（見 [APFS 卷結構](../macos_apfs_volume_structure/)）後，這個混淆就消除了。

[disk-report](https://github.com/tarrragon/scripts) 腳本的完整診斷模式會列出已安裝的 Simulator runtime，多版本時標記 redundant。移除多餘版本的操作流程見 [移除多餘 iOS Simulator](../macos_remove_redundant_ios_simulators/)。
