---
title: "macOS App Sandbox 與 ~/Library/Containers 架構"
date: 2026-07-05
slug: "macos-app-sandbox-container"
description: "排查磁碟空間時看到 ~/Library/Containers 佔了幾十 GB、想知道哪些能清時需要理解的沙箱機制。Container 是 App 的完整家目錄副本，結構固定但內容分快取與資料兩類。"
tags: ["macos", "disk-space", "app-sandbox"]
---

`~/Library/Containers` 是 macOS 沙箱（App Sandbox）機制的產物。每個啟用沙箱的 App 在這裡有一個獨立的目錄，作為該 App 的隔離環境。排查磁碟空間時，Containers 常是 `~/Library` 裡最大的子目錄之一，理解它的結構才能判斷哪些佔用是可以清除的快取、哪些是動不得的使用者資料。

## 沙箱的設計目的

App Sandbox 限制每個 App 只能存取自己的資料，不能碰其他 App 或使用者的檔案。這個隔離不是建議性的——沙箱由作業系統核心強制執行，App 程式碼裡寫了讀取其他 App 目錄的路徑，系統會拒絕。

Mac App Store 上架的 App 必須啟用沙箱。非 App Store 分發的 App 可以選擇不啟用，但越來越多開發者主動啟用以獲得使用者信任。

每個沙箱 App 拿到的是一個完整的家目錄副本——裡面有 `Documents`、`Library`、`Downloads` 等跟使用者家目錄一樣的子目錄，但 App 看到的路徑是自己的副本，不是使用者真正的家目錄。這些副本就放在 `~/Library/Containers/<bundle-id>/Data/` 下。

## Container 的內部結構

每個 Container 的結構是固定的：

```text
~/Library/Containers/<bundle-id>/
├── .com.apple.containermanagerd.metadata.plist  # 容器 metadata
└── Data/
    ├── Documents/      # App 的文件（使用者資料）
    ├── Library/        # App 的 Library（設定、快取、資料庫）
    │   ├── Caches/     # 快取（可安全清除）
    │   ├── Preferences/# 設定
    │   └── ...
    ├── Downloads/      # 有的是 symlink 到使用者的 ~/Downloads
    ├── Desktop/        # 通常是 symlink
    ├── tmp/            # 暫存
    └── StoreKit/       # App Store 相關
```

`Downloads`、`Desktop`、`Movies`、`Music`、`Pictures` 多數是 symlink（符號連結）指向使用者的對應目錄——沙箱允許 App 透過使用者授權存取這些位置。`du` 加 `-x` 旗標時不會跨越 symlink 計入，所以不會重複計算。

## 命名慣例：bundle ID vs UUID

Container 目錄的命名方式取決於 App 的來源。

**Bundle ID**（App 的唯一識別碼，格式為反向域名，例如 `com.amazon.Lassen`）：Mac 原生 App 使用 bundle ID 當目錄名。從名字就能辨識——`com.amazon` 是 Amazon、`com.docker.docker` 是 Docker。

**UUID**（例如 `D678BD0C-AEB0-4E05-B0D2-58F5C45F0207`）：[iOS App on Mac](../macos_ios_app_on_mac/) 使用 UUID 當目錄名，從名字完全無法辨識是哪個 App。辨識方法是讀 Container 根部的 `.com.apple.containermanagerd.metadata.plist`（見 [辨識 App 容器](../macos_identify_app_containers/)）。

## 佔用的兩類：快取 vs 資料

清理 Container 時要判斷佔用的性質——快取刪了會自動重建，資料刪了就消失。

**快取類**（`Data/Library/Caches/`、`Data/tmp/`）：App 產生的衍生物，刪除後 App 自動重建。清除零風險，最多讓 App 下次啟動慢一點或需要重新登入。

**資料類**（`Data/Documents/`、`Data/Library/Application Support/`）：使用者資料——遊戲的下載資源、電子書的離線書庫、聊天紀錄、筆記資料庫。刪除後資料消失，要從雲端重新下載（如果有雲端同步的話）。

兩類的大小比例因 App 而異。遊戲類 App 的 Documents 常佔 90% 以上（語音包、素材、更新包），快取比例很低。瀏覽器類 App 則相反，快取常佔大宗。排查時逐 App 看 `Data/Documents` 和 `Data/Library/Caches` 的大小分佈，才能判斷清掉能回收多少、風險是什麼。

## 跟 Application Support 的分工

沙箱 App 的資料全部在自己的 Container 裡。非沙箱 App 的資料則散在 `~/Library` 的公共位置——`Application Support`、`Caches`、`Preferences` 等。同一個開發商的 App 可能有些啟用沙箱（Container 裡一份完整資料）、有些沒有（散在公共位置），兩者的佔用要分開看。

[App 聚合佔用報告](../macos_app_footprint_report/) 的 `app-report` 腳本把 Container 和公共位置的佔用聚合回各 App，就是處理這個分散的問題。

## Group Containers

`~/Library/Group Containers/` 是同一個開發商旗下多個 App 共享資料的位置。目錄名前面多一段 team ID（10 碼英數，像 `HUAQ24HBR6.dev.orbstack`）。清理時要注意：動一個 Group Container 可能影響同廠商的多個 App。
