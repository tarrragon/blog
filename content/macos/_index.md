---
title: "macOS"
slug: "macos"
description: "macOS 系統架構、磁碟與程序資源、開發環境設定。從 APFS 卷結構到程序表配額，理解機制後自己判斷。"
tags: ["macos", "系統管理"]
---

macOS 的系統架構、磁碟空間管理、程序資源配額、開發環境設定。每篇文章教一個獨立的機制或概念，讀者理解機制後能自己判斷問題、不需要查表。

## 系統架構

基礎概念，其他文章的引用基礎：

- [APFS 卷結構與空間池](macos_apfs_volume_structure/) — container / volume / volume group 三層架構、du / df / diskutil 數字不同的原因
- [Preboot 卷：從 Intel 的 1G 到 Apple Silicon 的 8G](macos_preboot_volume_check/) — Cryptex 安全更新機制為什麼改變了 Preboot 的大小
- [iOS Simulator Runtime 架構](macos_ios_simulator_runtime_architecture/) — 為什麼一組 runtime 要 16G、DMG 掛載成獨立 APFS Container 的機制
- [App Sandbox 與 Container 架構](macos_app_sandbox_container/) — ~/Library/Containers 的設計目的、內部結構、bundle ID 命名慣例
- [iOS App on Mac](macos_ios_app_on_mac/) — Apple Silicon 跑 iOS App 的機制、UUID 容器、容器殘留

## 程序與資源配額

程序表格位是磁碟以外的另一類有限資源，機制與排查合在同一篇：

- [殭屍程序與使用者程序上限](macos_process_limit_zombie_reaping/) — 兩道 fork 關卡與一道 setrlimit 天花板、exit 與 wait 兩階段、reparenting 一次回收，附指認堆積父程序的三步診斷

## 系統介面程序

`ControlCenter`、`SystemUIServer` 這類由 launchd 看管、畫出選單列圖示與控制中心的程序卡住時的判讀與重啟：

- [選單列的控制中心沒有回應](macos_control_center_unresponsive/) — 依位置查出選單列圖示的擁有程序、等待游標代表的狀態、從 ps 的 STAT 與 %CPU 分辨空轉與等待、launchd 的 KeepAlive 讓 killall 等於重啟（Dock、Finder、SystemUIServer 同一套設定）、重啟後用 launchctl print 與 top 確認、系統診斷報告與 sample 的呼叫堆疊讀法、重啟單一程序與登出、重新開機的取捨

## 磁碟空間管理

建立在系統架構上的排查與操作：

- [磁碟空間診斷流程](macos_disk_space_diagnosis/) — 從 container 到家目錄逐層收斂的排查順序
- [App 聚合佔用報告](macos_app_footprint_report/) — 把散落在 ~/Library 各處的 App 資料聚合回各 App
- [辨識 App 容器](macos_identify_app_containers/) — 讀 plist 辨識 UUID 容器是哪個 App
- [移除多餘 iOS Simulator](macos_remove_redundant_ios_simulators/) — 透過 simctl 移除舊版 runtime
- [開發機的定期空間清理](macos_developer_periodic_cleanup/) — 依刪除後由誰重建分類：專案產物、套件與 App 的快取、並存的工具鏈版本（Gradle、NDK、Android 模擬器映像、iOS runtime、Flutter SDK）、容器虛擬磁碟、模擬器裝置與自己開發的 App 的沙箱容器

## 環境設定

- [新機基礎建設](macos_new_machine_setup/) — 一台新 Mac 從開箱到能開發的設定流程
- [BSD userland 與 GNU 的差異](macos_bsd_userland_vs_gnu/) — 為何 GNU 習慣（timeout、sed -i、readlink -f、bash 語法）在 macOS 會撞、怎麼繞
- [多桌面快捷鍵](macos_muti_spaces/) — Mission Control 的桌面切換設定

## Backlog

| 項目                                                                                                                                                       | 類型 | 前置條件                                  | 規模 |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ----------------------------------------- | ---- |
| `WindowServer` 本身高 CPU 的判讀：〈選單列的控制中心沒有回應〉量到 `WindowServer` 在 `ControlCenter` 重啟前後都在 40% 以上，來源沒有追查，站內沒有文章寫它 | 主章 | 需要一次可重現的量測（逐一關掉 App 對照） | 中   |

---

底下自動列出本資料夾的所有文章、依日期排序。
