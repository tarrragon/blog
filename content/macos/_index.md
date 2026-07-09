---
title: "macOS"
slug: "macos"
description: "macOS 系統架構、磁碟管理、開發環境設定。從 APFS 卷結構到 App Container 辨識，理解機制後自己判斷。"
tags: ["macos", "系統管理"]
---

macOS 的系統架構、磁碟空間管理、開發環境設定。每篇文章教一個獨立的機制或概念，讀者理解機制後能自己判斷問題、不需要查表。

## 系統架構

基礎概念，其他文章的引用基礎：

- [APFS 卷結構與空間池](macos_apfs_volume_structure/) — container / volume / volume group 三層架構、du / df / diskutil 數字不同的原因
- [Preboot 卷：從 Intel 的 1G 到 Apple Silicon 的 8G](macos_preboot_volume_check/) — Cryptex 安全更新機制為什麼改變了 Preboot 的大小
- [iOS Simulator Runtime 架構](macos_ios_simulator_runtime_architecture/) — 為什麼一組 runtime 要 16G、DMG 掛載成獨立 APFS Container 的機制
- [App Sandbox 與 Container 架構](macos_app_sandbox_container/) — ~/Library/Containers 的設計目的、內部結構、bundle ID 命名慣例
- [iOS App on Mac](macos_ios_app_on_mac/) — Apple Silicon 跑 iOS App 的機制、UUID 容器、容器殘留

## 磁碟空間管理

建立在系統架構上的排查與操作：

- [磁碟空間診斷流程](macos_disk_space_diagnosis/) — 從 container 到家目錄逐層收斂的排查順序
- [App 聚合佔用報告](macos_app_footprint_report/) — 把散落在 ~/Library 各處的 App 資料聚合回各 App
- [辨識 App 容器](macos_identify_app_containers/) — 讀 plist 辨識 UUID 容器是哪個 App
- [移除多餘 iOS Simulator](macos_remove_redundant_ios_simulators/) — 透過 simctl 移除舊版 runtime

## 環境設定

- [新機基礎建設](macos_new_machine_setup/) — 一台新 Mac 從開箱到能開發的設定流程
- [BSD userland 與 GNU 的差異](macos_bsd_userland_vs_gnu/) — 為何 GNU 習慣（timeout、sed -i、readlink -f、bash 語法）在 macOS 會撞、怎麼繞
- [多桌面快捷鍵](macos_muti_spaces/) — Mission Control 的桌面切換設定

---

底下自動列出本資料夾的所有文章、依日期排序。
