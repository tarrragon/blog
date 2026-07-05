---
title: "iOS App on Mac：Apple Silicon 跑 iOS App 的機制"
date: 2026-07-05
slug: "macos-ios-app-on-mac"
description: "Apple Silicon Mac 可以直接跑 iOS App，這些 App 的容器用 UUID 命名、不出現在 /Applications、移除後容器可能殘留。理解這個機制後才能判斷 ~/Library/Containers 裡佔了幾 GB 的 UUID 目錄是什麼。"
tags: ["macos", "apple-silicon", "disk-space"]
---

Apple Silicon Mac（M1 及之後）可以直接執行 iPhone 和 iPad App，不需要模擬器。這個功能在 macOS 11 Big Sur 引入，讓使用者從 Mac App Store 安裝 iOS App 像安裝 Mac App 一樣簡單。但 iOS App on Mac 在系統裡的行為跟原生 Mac App 有幾個關鍵差異，這些差異影響磁碟空間排查和 App 管理。

## 執行機制

Apple Silicon 的 CPU 架構（arm64）跟 iPhone/iPad 相同，所以 iOS App 的二進位可以直接在 Mac 上跑，不需要轉譯或模擬。macOS 提供一個相容層，把 iOS 的觸控 API 對應到滑鼠和鍵盤操作，讓 iOS App 在 Mac 上有基本的操作體驗。這個相容層跟 Mac Catalyst（開發者主動移植 iPad App 到 Mac 的框架）是不同的機制——iOS App on Mac 不需要開發者做任何修改。

這跟 [iOS Simulator](../macos_ios_simulator_runtime_architecture/) 是完全不同的機制。Simulator 跑的是為 Mac CPU 重新編譯的 iOS 框架，用於開發測試；iOS App on Mac 跑的是 App Store 上為 iPhone 編譯的原始二進位，用於日常使用。

## Container 用 UUID 命名

原生 Mac App 的 [沙箱容器](../macos_app_sandbox_container/) 用 bundle ID 當目錄名（例如 `com.amazon.Lassen`）。iOS App on Mac 的容器用 UUID 當目錄名（例如 `D678BD0C-AEB0-4E05-B0D2-58F5C45F0207`），從名字完全看不出是哪個 App。

UUID 命名的原因是 iOS App 的容器管理走的是 iOS 的路徑——iOS 上本來就用 UUID 組織 App 資料，macOS 的相容層沿用了這個設計。

辨識 UUID 容器的方法是讀 `.com.apple.containermanagerd.metadata.plist` 裡的 `MCMMetadataIdentifier` 欄位，需要 Full Disk Access 權限。操作流程見 [辨識 App 容器](../macos_identify_app_containers/)。

## 遊戲是主要的空間消耗者

iOS App on Mac 裡佔用最大的幾乎都是遊戲。手遊的語音包、素材、更新包動輒數 GB，這些資源下載到 Container 的 `Data/Documents/` 裡。一台 256G Apple Silicon Mac 上的實際案例：

- Epic Seven（第七史詩，`com.stove.epic7.ios`）：9.7G
- Arknights（明日方舟台服，`tw.txwy.ios.arknights`）：8.7G

這些資源是可重新下載的衍生物，帳號進度在遊戲伺服器端。刪除本地容器不影響帳號，重裝時需要重新下載資源。

## 空間佔用在 Data 卷上

iOS App on Mac 的容器跟所有 App 資料一樣，儲存在 [APFS container](../macos_apfs_volume_structure/) 的 Data 卷上，共用空間池。遊戲類 App 的容器動輒數 GB，直接壓縮 Data 卷的可用空間。

## 不出現在 /Applications

iOS App on Mac 不一定出現在 `/Applications` 資料夾或 Finder 的應用程式列表裡。它們的 `.app` 本體放在系統管理的位置（通常在 `/Applications` 的子目錄或 App Store 的快取路徑），Launchpad 能看到但 Finder 的應用程式資料夾不一定列出。

用 `du -shx /Applications/*.app` 排查空間大戶時會完全漏掉 iOS App。它們的空間佔用只出現在 `~/Library/Containers/` 裡，而且因為 UUID 命名，不展開辨識就不知道是哪個 App。

## 移除後容器可能殘留

從 Launchpad 長按刪除或從 App Store「已購項目」移除 iOS App 後，它的 Container 目錄不一定跟著消失。macOS 的清理機制有時會延遲或跳過。殘留的 Container 佔用空間但不再有對應的 App。

確認殘留的方式：Container 的 plist 裡有 `MCMMetadataIdentifier`（bundle ID），但系統裡找不到對應的已安裝 App。這時整個 Container 目錄可以安全刪除。

## 已下架 App 的風險

iOS App Store 裡的 App 可能被開發者下架或因區域限制無法取得。如果一個 iOS App on Mac 已經從 App Store 移除，刪掉本地容器和 App 後就無法重新安裝。對於有替代品的 App 影響不大；對於特定地區限定的遊戲（例如只在日本或台灣 App Store 上架的版本），刪除前要考慮這個不可逆性。
