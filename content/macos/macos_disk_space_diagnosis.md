---
title: "macOS 磁碟空間被吃光的診斷流程"
date: 2026-06-26
description: "Mac 空間莫名歸零、清 cache 沒救、或空間掉了又回來時的排查順序。避開 sparse 假大小和本地快照浮動的誤判。含 disk-report 腳本。"
tags: ["macos", "disk-space", "apfs", "time-machine", "troubleshooting", "tooling"]
---

一台原本還有約 30G 餘裕的 Mac，使用幾小時後空間全部歸零，清過系統各種 cache 也沒有改善。這次排查的重點是順序與判讀依據：用什麼順序找、用哪個數字判斷，最後刪了什麼反而次要。順序對了，就能避開兩個讓人空轉的陷阱。

最後把整套診斷固化成一個唯讀的 `disk-report` 腳本，往後同類情況可以一行指令重跑。

## 先確認問題是「真的滿」還是「浮動的假象」

排查磁碟的第一步是分辨空間到底去哪：是被真實檔案佔走，還是被系統的快照與 purgeable（系統可隨時回收的緩衝空間）暫時佔住。這兩者的處理方式完全不同，先分清楚才不會白清。

在 [APFS](../macos_apfs_volume_structure/)（Apple File System，macOS 的預設檔案系統）上，根目錄 `/` 是唯讀的系統封印卷，真正存放使用者資料的是 `/System/Volumes/Data`，而它們和其他卷（[Preboot](../macos_preboot_volume_check/)、Recovery、VM、模擬器 runtime）共用同一個 container（容器，APFS 管理空間的最上層單位）的空間池。判斷「還剩多少」要看整個 container 的可用空間，而不是單一卷的數字。

```bash
df -h /System/Volumes/Data
diskutil info /System/Volumes/Data | grep -iE "Container Free Space|Container Total Space"
```

這次的結果是資料卷 100% 滿、整個 container 只剩約 591MB。確認確實滿載、不是顯示誤差，後面才值得花力氣找佔用大戶。

## 「空間掉了又回來」的根因：本地快照與 purgeable

空間在幾小時內反覆消長、清 cache 卻無效，最常見的原因是 Time Machine 的本地快照（local snapshots）加上 macOS 的 purgeable 空間，而不是某個看得見的檔案。這是排查時要先排除的一條線。

本地快照的運作方式是：Time Machine 啟用時，系統約每小時自動建立一張快照「凍結」當下狀態，好讓本地也能做時光機回溯。這些被凍結的資料，正是先前以為已刪除、卻怎麼清都不會釋放的空間。快照保留約 24 小時（Apple 的 thinning 策略，觀察值），或在磁碟空間壓力過大時提前清除；後者正是「過一陣子空間又回來」的來源。若從未設定 Time Machine，這條線可跳過——沒啟用就不會有 local snapshot。

```bash
tmutil listlocalsnapshots /System/Volumes/Data
```

這次查的時候快照數是 0，但這不代表它不是元兇——恰恰相反，是磁碟已經滿到讓系統把快照全數清光了。判讀訊號是：若這個指令平常列出多筆快照、且磁碟空間在數字上頻繁浮動，浮動量就來自這裡，跟手動清的 cache 無關。根治方向是把總用量降下來、讓磁碟保有餘裕，系統就不會一直貼著上限狂建狂清快照。

purgeable 是同一條線的另一半，但它沒有好用的精確讀數。`diskutil apfs list` 能看 container 層的概況，而 purgeable 主要由快照與系統快取構成、本來就會自己浮動。處理方式跟快照一樣：把總用量降下來、讓系統在空間有壓力時自行釋放，而不是找指令直接清它。「沒有直接讀數」本身就是判讀邊界——看到可用空間和「實際檔案總和」對不上時，差額多半就在這塊浮動緩衝，不必懷疑是哪個檔案在搞鬼。

## 用實際佔用值找大戶，避開 sparse 假大小

找佔用大戶要用 `du`（實際佔用的磁碟區塊）排序，不能依賴 `ls -l` 顯示、或 `find -size` 篩選所用的邏輯大小。對一般檔案兩者相同，但對 sparse 檔（稀疏檔）差距可以是好幾十倍，誤判會追錯目標。

這次就踩到這個陷阱。`find` 列出近期修改的大檔時，OrbStack（一套容器與 VM 執行環境）的虛擬磁碟映像顯示為 228G，看起來像頭號兇手；但用 `du` 一量，實際佔用只有 1.9G。同樣地，macOS Podcasts 在 tmp 塞的一堆 `.tmp.resize.img` 顯示有數十個檔，實際只佔 3.5M。這些都是 sparse 檔：宣告了很大的邏輯大小，但只有寫入過的區塊才真正佔磁碟。

```bash
# 實際佔用（正確）
du -sh ~/some/large.img

# 顯示大小（對 sparse 檔會嚴重高估，誤判用）
ls -lh ~/some/large.img
```

定位順序是由外往內逐層收斂：先看家目錄前 20 大，鎖定最大的子樹（這次是 `~/Library` 70G 左右），再往下展開 `~/Library/Application Support`、[`~/Library/Containers`](../macos_app_sandbox_container/)，直到找到具體的檔案或目錄。Containers 裡的 UUID 目錄是 [iOS App on Mac](../macos_ios_app_on_mac/) 的容器，辨識方式見 [Container 辨識](../macos_identify_app_containers/)。

```bash
du -shx ~/* ~/.[!.]* 2>/dev/null | sort -rh | head -20
du -shx ~/Library/* 2>/dev/null | sort -rh | head -12
```

`-x` 讓 `du` 不跨越檔案系統邊界，避免把掛載進來的唯讀卷（例如 iOS 模擬器 runtime）重複計入；`~/.[!.]*` 這個寫法只展開以單一點開頭的隱藏檔，排除掉 `.` 和 `..` 兩個會被一般 `.*` 誤抓進來、算出整個家目錄大小的假項目。

## 這次找到的佔用大戶與處理

定位出來的大戶集中在開發工具鏈與閒置的本地資料，多數可逆、刪了之後需要時會自動重建或可重新下載。下面的項目與數字都是這台機器的實測，換一台機器組成會完全不同；值得帶走的是每一項背後的判讀問題，不是這份清單本身。具體刪除指令因工具而異（Android Studio GUI、`rm -rf`、`ollama rm`），本文只做診斷與定位，刪除操作留給各工具自身的文件。以下逐項說明判讀依據。

| 項目                        | 實際佔用 | 處理判斷                                                |
| --------------------------- | -------- | ------------------------------------------------------- |
| 舊版 Android NDK            | 約 3G    | 裝了多版、保留專案實際引用的版本，刪最舊                |
| 用不到的 AVD + system-image | 約 3G    | 一個 API 版本一組、停用的版本連 AVD 帶映像一起刪        |
| Claude 桌面 Cowork 沙箱 VM  | 約 11G   | 只在使用桌面 App 的本地 agent 功能時才佈建，不用則可刪  |
| ollama 本地模型             | 約 9G    | 改用雲端後閒置的大模型可刪，小的 embedding 模型常是依賴 |
| Xcode iOS DeviceSupport     | 約 4.5G  | 實體裝置接線除錯的符號快取，重連會自動重建              |

Android NDK 的判讀要回到「誰在用它」：這次專案是 Flutter，NDK 版本由 `flutter.ndkVersion` 決定，而不是專案自己 pin。查當前 Flutter 要求的版本後發現，本機裝的兩版都是舊 Flutter 留下的殘留，於是保留較新的一版、刪掉最舊的。判斷可不可刪的關鍵是先確認「現在到底用哪版」，而不是看修改日期就動手。

Claude 桌面的 `vm_bundles` 是最大單一項目（11G）。它是桌面 App 的 Cowork 功能在本地沙箱 VM 裡執行程式用的根檔案系統映像。關鍵判讀是：它不是每次開 App 就重建——映像的修改日期停在數月前，是一次性佈建、之後沿用。只有實際使用 Cowork 沙箱時才會佈建和更新。所以對只用終端機 CLI、桌面 App 僅拿來聊天的人，這 11G 是純佔用，可以安全刪除；唯一後果是哪天實際開了 Cowork session，它會重新佈建。

剩下三項的判讀各有自己的關鍵問題。閒置的 AVD 與 system-image 是「一個 API 版本一組」的綁定，停用某個 Android 版本時要連 AVD 帶它依賴的系統映像一起刪，只刪一邊會留下半套。ollama 本地模型的判斷是「改用雲端後還會不會在本地跑」，閒置的大模型可刪，但小的 embedding 模型常被其他工具當依賴、刪了會牽連（ollama 模型的累積速度與專屬清理 idiom，見 [本地 LLM 的資源管理](/llm/01-local-llm-services/hands-on/resource-management/)）。Xcode 的 iOS DeviceSupport 則是實體裝置接線除錯時產生的符號快取，可以放心刪——下次接上同一台裝置除錯時 Xcode 會自動重建。

這幾項合計回收約 17G，可用空間從約 591MB 拉回到 18G，磁碟脫離滿載。

## 把診斷固化成 disk-report 腳本

一次性查完之後，把這套順序寫成腳本的價值是：下次同類情況不必重新回想指令與判讀順序，一行就能重跑，而且固定先看快照、再用實際佔用值，不會又掉進 sparse 假大小的陷阱。

腳本收在公開 repo [tarrragon/scripts](https://github.com/tarrragon/scripts)，而不是放進某個專案的 `bin/`。它跟任何專案無關，連到個人 bin 才能在任何地方直接呼叫，也不會污染專案 repo。安裝方式是 clone 下來、把腳本本體 symlink 到 `~/.local/bin`：

```bash
git clone https://github.com/tarrragon/scripts.git ~/Projects/scripts
ln -s ~/Projects/scripts/disk-report/disk-report ~/.local/bin/disk-report
```

這一步預設 `~/.local/bin` 已在 PATH 上。若還沒設定，做法見 [macOS 新機基礎建設](../macos_new_machine_setup/) 的對應項目。腳本刻意設計成唯讀：只報告、不刪除，刪什麼由人看完報告再決定。

```bash
disk-report              # 完整診斷：總覽 + 快照狀態 + 各層大戶 + 開發環境可清項
disk-report --growing    # 只看過去 180 分鐘內長大的大檔（抓動態暴增最快）
disk-report --growing 60 # 改成過去 60 分鐘
```

`--growing` 模式對應的是本文開頭那個「幾小時內暴增」的情境：當空間正在快速消失、想抓現行犯時，直接列出近期被寫入的大檔，比逐層 `du` 更快定位。

```bash
find "$HOME" -type f -size +50M -mmin -180 2>/dev/null \
  -exec du -h {} \; 2>/dev/null | sort -rh | head -25
```

50M 的下限是為了過濾日常小檔雜訊、鎖定單一大檔暴增；若懷疑是大量小檔累積吃空間（如快取碎片），這個門檻抓不到，要回逐層 `du` 看目錄總量。排序依據同樣是 `du` 的實際佔用值，而不是 `find -size` 的邏輯大小門檻，理由和前面一致：避免 sparse 檔的邏輯大小把排序帶歪。

## 排查順序總結

這次的方法可以收斂成一條固定順序，往後遇到任何「磁碟莫名變滿」都先照這條走：

1. 先看 container 可用空間，確認是真滿還是顯示誤差。
2. 再查本地快照與 purgeable，排除「掉了又回來」的浮動來源。
3. 用 `du -shx` 由外往內逐層找大戶，全程以實際佔用值判斷，不信 `ls` / `find` 的顯示大小。
4. 對每個大戶問「現在誰在用它」再決定刪不刪，可逆的優先清。
5. 把整套順序固化成唯讀腳本，下次一行重跑。

第 3 步若收斂到 `~/Library` 這種多個 App 共用的大目錄，按目錄統計只能看出 Caches、Containers 各多大，看不出是哪幾個 App 佔的。把這棵子樹再按 App 拆開的做法，見 [macOS App 聚合佔用報告](../macos_app_footprint_report/)。
