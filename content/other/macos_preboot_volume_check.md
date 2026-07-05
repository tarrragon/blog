---
title: "macOS Preboot 卷空間檢查：Apple Silicon 的 Cryptex 為什麼吃 8G"
date: 2026-07-05
slug: "macos-preboot-volume-check"
description: "磁碟排查時看到 Preboot 佔 8G+ 想知道正不正常、能不能清時查。Intel Mac 才 1-2G 的經驗會在 Apple Silicon 上產生誤判。"
tags: ["macos", "disk-space", "apfs", "apple-silicon", "troubleshooting"]
---

用 `diskutil apfs list` 查磁碟空間時，Preboot 卷顯示 8.5G。如果你的參照基準是 Intel Mac 時代的 1-2G，這個數字看起來異常偏高，直覺是「有舊 macOS 殘留可以清」。這次排查的結論是：Apple Silicon + macOS 15 的 Preboot 佔 8G 左右是正常值，不是殘留，也不該手動清。異常偏高的判讀訊號是特定結構指標（多個 Volume Group UUID、restore-staged 堆積），絕對大小本身不是。

## Preboot 卷的角色

Preboot 是 APFS container 裡的一個獨立卷，專門存放開機過程需要的資料 — 在 Data 卷解鎖之前，系統就要從這裡讀取開機載入器、核心快取、安全驗證票證。它跟 System 卷（唯讀的作業系統本體）和 Data 卷（使用者資料）共用同一個 container 的空間池，所以 Preboot 佔多少，直接影響 Data 卷可用的空間。

在 Intel Mac 上，Preboot 裡主要就是一組 boot.efi 和少量開機設定，大小穩定在 1-2G。Apple Silicon 改變了這個數字，原因是 Cryptex。

## Cryptex：Preboot 從 2G 跳到 8G 的原因

Cryptex（Cryptographically Sealed Extension）是 Apple 從 macOS 13 開始引入的機制，讓 Safari 和系統安全元件可以獨立於整個 OS 更新來部署。在此之前，修一個 Safari 漏洞就要推一整版 macOS 更新；有了 Cryptex，這些元件封裝成獨立的簽章 DMG，掛載後疊加到系統卷上層。

這些 Cryptex DMG 就住在 Preboot 卷裡，佔用了主要空間。在這台 macOS 15.3.1 的機器上，Preboot 的結構如下：

```text
/System/Volumes/Preboot/<Volume-Group-UUID>/
├── cryptex1/current/       # 當前 Cryptex — 佔用主力
│   ├── os.dmg              # 系統安全元件 DMG (5.4G)
│   ├── os.clone.dmg        # APFS clone (共用底層區塊)
│   └── app.dmg             # App 層元件 (22M)
├── restore-staged/         # 已下載但未套用的更新資料 (1.6G)
│   ├── Firmware/           # 韌體映像
│   ├── *.dmg.aea           # 加密的更新 DMG
│   └── kernelcache.*       # 各機型的核心快取
├── restore/                # 復原模式用的開機資料 (861M)
├── boot/                   # 開機載入器 (47M)
└── var/, usr/, ...         # 其他開機輔助資料 (~25M)
```

`os.dmg` 和 `os.clone.dmg` 是 APFS clone — 底層共用同一份資料區塊，`du` 會各算一次報 11G，但 `diskutil` 只計算實際佔用的區塊，所以報 5.4G。這是排查時第一個容易踩到的誤差來源：用 `du` 量 Preboot 會高估，用 `diskutil info` 看 Volume Used Space 才是實際數字。

## 檢查方法

排查 Preboot 是否正常的步驟分三層：先看大小是否在合理範圍、再看內部結構有沒有異常指標、最後確認沒有殘留的舊安裝。

### 第一層：確認實際大小

```bash
# 用 diskutil 看實際佔用（不受 APFS clone 膨脹影響）
diskutil info /System/Volumes/Preboot | grep "Volume Used Space"
```

Apple Silicon + macOS 14-16 的正常範圍大約在 6-10G。超過 12G 才值得往下查第二層。如果你的機器是 Intel Mac 或 macOS 12 以下，Cryptex 不存在，正常值是 1-3G。

### 第二層：檢查內部結構

```bash
# 找到 Volume Group UUID
ls /System/Volumes/Preboot/ | grep -E '^[0-9A-F]{8}-'

# 各子目錄大小
VGUUID="$(ls /System/Volumes/Preboot/ | grep -E '^[0-9A-F]{8}-' | head -1)"
du -shx /System/Volumes/Preboot/"$VGUUID"/* 2>/dev/null | sort -rh

# Cryptex 細節
du -shx /System/Volumes/Preboot/"$VGUUID"/cryptex1/current/* 2>/dev/null | sort -rh

# Cryptexes 目錄（系統層）
du -shx /System/Volumes/Preboot/Cryptexes/* 2>/dev/null | sort -rh
```

正常結構的特徵：

- `cryptex1/current/` 佔最大宗（5-7G），裡面是 `os.dmg` + `os.clone.dmg` + `app.dmg`
- `restore-staged/` 在 0-2G 之間浮動，取決於是否有待套用的更新
- `restore/` 約 800M-1G
- `boot/` 約 50M
- Volume Group UUID 只有一個

### 第三層：排除舊安裝殘留

```bash
# 列出所有 Volume Group UUID
ls /System/Volumes/Preboot/ | grep -E '^[0-9A-F]{8}-'

# 確認當前系統的 Volume Group UUID
diskutil info /System/Volumes/Data | grep "Volume Group" | head -1
```

如果 Preboot 裡出現**多個** UUID 目錄，表示曾經有過多重 macOS 安裝。只有跟當前 Data 卷的 Volume Group UUID 對應的那個是必要的，其他可能是舊安裝殘留。這是 Preboot 異常偏大（超過 15G）最常見的原因。

## 異常指標與對應處理

| 指標                                                       | 意義                               | 處理                                               |
| ---------------------------------------------------------- | ---------------------------------- | -------------------------------------------------- |
| 多個 Volume Group UUID 目錄                                | 舊 macOS 安裝殘留                  | 確認哪個是當前系統後可刪除多餘的                   |
| `restore-staged/` 超過 3G 且日期距今超過一個月             | 下載了更新但套用失敗或被中斷       | 嘗試完成系統更新；更新完成後系統會自動清理         |
| `cryptex1/` 裡有 `current` 以外的子目錄                    | 可能有舊版 Cryptex 未清除          | 正常情況系統會自動替換，異常時重新安裝最新安全更新 |
| `Cryptexes/Incoming` 跟 `Cryptexes/OS` 大小相近且都超過 5G | 正常（Incoming 是更新通道的暫存）  | 不處理                                             |
| 整體超過 15G 但只有一個 UUID                               | Cryptex 或 restore-staged 異常堆積 | 確認系統更新狀態，必要時聯繫 Apple Support         |

`restore-staged` 的日期判讀有一個要注意的地方：這次實測中，`restore-staged` 裡的 `RestoreVersion.plist` 顯示的是 macOS 26.3.1（build 25D2128），而當前系統是 15.3.1（build 24D70）。版本號跨了一整個大版本，但檔案日期是 2025 年 2 月。這表示 `restore-staged` 裡放的不一定是「待套用到當前系統的更新」，也可能是系統為了未來升級預先 staging 的資料。不要因為版本號不匹配就判定它是殘留該清。

## 不該做的事

Preboot 是系統安全啟動鏈的一部分，手動刪除任何檔案都可能導致無法開機或安全更新失效。即使你確認某個 UUID 目錄是舊安裝殘留，直接 `rm -rf` 也不是正確做法，因為 APFS 的 snapshot 和 clone 關係可能讓刪除動作影響到你沒預期的區塊。

正確的清理路徑：

- **舊安裝殘留**：用 macOS Recovery 模式重新安裝 macOS（不會清使用者資料），讓系統自己整理 Preboot
- **卡住的系統更新**：在「系統設定 > 一般 > 軟體更新」完成或重新下載更新
- **Cryptex 異常**：安裝最新的安全更新，系統會替換 Cryptex 內容

在磁碟空間的排查順序裡，Preboot 應該排在最後。它的大小基本固定、使用者控制不了、清理風險高。同樣的排查時間花在 [~/Library 大戶定位](../macos_disk_space_diagnosis/) 或 [App 聚合佔用](../macos_app_footprint_report/) 上，回收效率高得多。

## 把檢查整合進 disk-report 腳本

Preboot 檢查的指令固定、判讀邏輯簡單，適合整合成自動化腳本。但它不適合獨立成一支腳本 — 單獨跑 Preboot 檢查的場景太少，幾乎只在「磁碟滿了、逐層排查」的流程中才會看它。比起另開一支 `preboot-report`，更合理的做法是在既有的 [disk-report](https://github.com/tarrragon/scripts) 裡新增一個 Preboot 段落，讓完整診斷時自動涵蓋。

腳本要做的事：

1. 用 `diskutil info` 取 Preboot 實際佔用，跟 10G 門檻比較
2. 計算 Volume Group UUID 數量，多於一個就標記
3. 如果 `restore-staged/` 存在且超過 2G，標記並顯示日期
4. 輸出一行摘要：正常 / 偏高但結構正常 / 有異常指標

不需要做的事：不替使用者刪任何東西（跟 disk-report / app-report 一樣唯讀）、不需要 `du` 逐檔列舉（`diskutil` 的卷級數字就夠判讀）、不需要解析 Cryptex 版本（那是 Apple 的更新機制內部細節，不影響空間判斷）。

新增段落的參考實作放在 [tarrragon/scripts](https://github.com/tarrragon/scripts) 的 `disk-report` 裡。
