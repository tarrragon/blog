---
title: "macOS 每個 App 到底吃多少空間：聚合佔用的 app-report 腳本"
date: 2026-06-27
description: "按目錄統計只能看出 Caches、Containers 各佔多少，答不出哪個 App 是大戶。這篇記錄一個把每個 App 散落在 ~/Library 各處的佔用聚合成單一數字的 app-report 腳本，以及為什麼 .app 的大小會嚴重低估真實佔用。"
tags: ["macos", "disk-space", "homebrew", "troubleshooting", "tooling"]
---

`du ~/Library/*` 只能列出 Caches、Containers 這些目錄各佔多少，答不出「Steam 這個 App 一共吃了多少」。原因是一個 App 的資料散落在 `~/Library` 好幾個不同位置，按目錄統計就拆不回它名下。這篇記錄一個把這些散落佔用聚合回各 App 的 `app-report` 腳本——搭配磁碟層的 [disk-report](../macos_disk_space_diagnosis/)，後者找出哪棵子樹最大，這篇把子樹拆到 App。

## 一個 App 的真實佔用不等於它的 .app 大小

判斷一個 App 吃多少空間，要算的是它的總足跡（footprint），而不是 `/Applications` 裡那顆 `.app` 的大小。`.app` 只是程式本體，App 跑起來產生的資料（下載內容、快取、登入狀態、設定、日誌）絕大多數寫在 `~/Library` 底下的好幾個不同位置，跟 `.app` 完全分家。

這台機器上最極端的例子是 Steam：它的 `.app` 只有 10.8M，但遊戲資料佔了 8.1G，兩者差了近 800 倍。只看 `/Applications` 的大小排序，Steam 會排在很後面，完全看不出它是全機第一大戶。同樣地，Amazon Kindle 的 `.app` 才 138M，書庫卻在沙箱容器裡佔了 3.2G。這就是為什麼「按目錄統計」和「按 App 統計」會給出完全不同的排行；要回答「哪個 App 該清」，必須把佔用聚合回 App。

## 佔用散落在 ~/Library 的哪些地方

聚合的第一步是知道一個 App 會把資料寫到哪些固定位置。下表只列與空間相關的主要位置（非 `~/Library` 全量），macOS 對它們有約定，每個位置承擔不同責任，也決定了它能不能安全清掉。

| 位置                                 | 放什麼                    | 清掉的後果               |
| ------------------------------------ | ------------------------- | ------------------------ |
| `/Applications/*.app`                | 程式本體                  | 等於移除 App             |
| `~/Library/Caches/`                  | 快取                      | 下次自動重建，安全       |
| `~/Library/HTTPStorages/`            | 網路快取（cookie / 暫存） | 多半要重新登入，大致安全 |
| `~/Library/Application Support/`     | 設定與使用者資料          | 掉資料                   |
| `~/Library/Containers/`              | 沙箱 App 的完整家目錄     | 掉資料                   |
| `~/Library/Group Containers/`        | 同廠商 App 共享的資料     | 掉資料、可能影響多個 App |
| `~/Library/Saved Application State/` | 視窗位置與復原狀態        | 下次開窗位置重置，無傷   |
| `~/Library/Logs/`                    | 日誌                      | 安全                     |

這張表的關鍵分界是「快取」與「資料」。`Caches` 和 `HTTPStorages` 是純衍生物，清掉只是讓 App 下次重新下載或重建，最多重新登入一次，所以是回收空間時的首選。`Application Support`、`Containers`、`Group Containers` 則是使用者資料，Steam 的遊戲、Kindle 的書庫、聊天記錄都在這裡，刪了就真的沒了。`Group Containers` 還要多一層留意：它是同一個開發商旗下多個 App 共享的目錄，動它可能同時影響好幾個 App。

腳本對每個 App 把上面這些位置全部找出來、用 `du` 量實際佔用、加總成一個數字，再附上逐項明細，讓人一眼看出「這 4G 裡有多少是可清的快取、多少是動不得的資料」。

## 命名不一致是聚合的主要難點

把資料夾正確歸給某個 App 的難點在於：macOS 對這些目錄沒有統一的命名規則。有些 App 用它的 bundle id（例如 `com.valvesoftware.steam`）當目錄名，有些直接用 App 的顯示名稱（例如 `Steam`），同一個 App 的不同位置甚至各用一種。

腳本的做法是對每個 App 先讀出它的 bundle id，然後 `Caches`、`Application Support`、`Logs` 這幾個位置兩種命名都比對一次，bundle id 專屬的位置（`Containers`、`HTTPStorages`、`Saved Application State`）則用 bundle id 找。`Group Containers` 又是另一種格式，名稱前面多一段開發商的 team id（10 碼英數，像 `ABCDE12345.group.com.foo`），因此改用 bundle id 做子字串比對。這套規則涵蓋了絕大多數 App，但用罕見自訂命名的資料仍可能漏抓，這是聚合式估算的固有邊界，腳本在輸出裡據實標明「可能漏抓」而不假裝是精確值。

## Homebrew 要分開算

透過 Homebrew 裝的工具不在 `/Applications`，需要獨立統計。佔用分兩類（概念詳見 [Homebrew 知識卡](/llm/knowledge-cards/homebrew/)）：命令列工具與函式庫（[formula](/llm/knowledge-cards/homebrew/)）在 `Cellar/`，GUI App 的下載 artifact 與 metadata（[cask](/llm/knowledge-cards/homebrew/)）在 `Caskroom/`。cask 安裝的 `.app` 本體實際放在 `/Applications`，已被前面的 App 聚合排行計入；`Caskroom/` 存的是安裝來源與版本資訊，體積通常遠小於 App 本體，兩邊不重複計。

這台機器的 formula 前幾名是開發語言執行環境：`dotnet@9` 634M、兩個版本的 `openjdk` 合計 600M、`mysql` 292M、`go` 258M。formula 會多版本並存（例如 `python@3.13` 和 `python@3.14` 各算各的），所以腳本把整個 formula 目錄一起計。除了已安裝的部分，腳本還列出 `brew --cache` 的下載快取，以及 `brew cleanup -n` 預估可回收的舊版本（`-n` 是 dry-run，只報告不刪），跟整支腳本的唯讀原則一致。

## 聚合一律用 du 取實際佔用

App 各位置的聚合一律用 `du -skx` 取實際佔用，而不是 `ls` / `find -size` 的邏輯大小。sparse 檔（稀疏檔）只有寫入過的區塊才真正佔磁碟，宣告的邏輯大小可能是實際佔用的數十倍；容器與資料目錄裡正好常有 VM 映像、容器磁碟這類 sparse 檔，拿邏輯大小加總會把整份聚合排行灌水。完整的 sparse 踩坑案例見 [disk-report 那篇](../macos_disk_space_diagnosis/)。

`-x` 讓 `du` 不跨越檔案系統邊界，避免把掛載進來的卷重複計入；`-k` 統一用 KB 當單位，方便把各位置的數字加總後再換算成人類可讀的 G / M。

## 實測結果

下面是這台機器的實測排行（名次因個人使用習慣而異）；要看的是聚合排行和「按目錄統計」給的印象差多少：

| App           | 總佔用 | 主要落點                             |
| ------------- | ------ | ------------------------------------ |
| Steam         | 8.1G   | data 8.1G（`.app` 只有 10.8M）       |
| Xcode         | 4.8G   | bundle 4.8G                          |
| Readmoo 看書  | 4.6G   | data 3.8G + bundle 816M              |
| Dia           | 4.1G   | cache 1.6G + bundle 1.3G + data 1.1G |
| Amazon Kindle | 3.3G   | container 3.2G（`.app` 才 138M）     |

全機掃到 65 個 App、聚合總計 48.2G。這份排行的價值在於它直接指向「該從哪裡下手」，而判讀邏輯可以套到任何人的排行上：本體小、資料大的 App（這台是 Steam、Kindle）要回收就得處理書庫與遊戲本身；純快取大的（這台是 Dia 的 1.6G）清掉零風險；本體就大的開發工具（Xcode、Android Studio）除非不再開發否則動不得。同一個總數字底下，可清的比例天差地別，這正是逐項明細要回答的問題。

## 聚合的邊界：總計不等於整機

這個 48.2G 是「能歸屬到已安裝 App 的部分」之和，不是 `~/Library` 的全量。[disk-report 那篇](../macos_disk_space_diagnosis/)量到的 `~/Library` 約 70G，差額落在幾類刻意不歸進單一 App 的位置。

最大的一塊是 `~/Library/Developer`（這台約 5.5G，幾乎全是 Xcode 的 DerivedData、CoreSimulator 與 iOS DeviceSupport）。它們是 Xcode 與模擬器產生的共用產物，硬塞給 Xcode 會誇大這顆 App、塞給別人又不對，app-report 比照 Homebrew 把它單獨列成一段（`app-report --dev`）。也因為這樣，上面排行裡的 Xcode 只算到 `.app` 本體，它的建置產物要看 Developer 那段——這也是為什麼 disk-report 會把「Xcode DeviceSupport」列為大戶，而逐 App 排行卻看不到：那筆資料正住在這個不歸單一 App 的位置。

其餘排除的還有 iCloud 與雲端硬碟的本地鏡像（`Mobile Documents`、`CloudStorage`）、已移除 App 留下的孤兒資料夾、以及 `Preferences`。排行掃的是 `/Applications`、`~/Applications`、`/Applications/Utilities` 與 Setapp、Mac App Store 裝的 App；直接從 DMG 跑、沒搬進 Applications 的 App 不會出現在排行，但它的 `~/Library` 資料若命名對得上仍可能部分計入。

還有一個方向相反的誤差要記得：這是估算不是精算。同一份資料若以 APFS clone 出現在多個被聚合的位置，逐位置分開跑 `du` 會各自計入（`du` 只在單次執行內對硬連結以 inode 去重，對 APFS clone 不去重），聚合值可能偏高。要看整個 `~/Library` 到底多大、由誰佔，回到 disk-report 的逐層 `du`。

## 固化成 app-report 腳本

把這套聚合邏輯寫成腳本，往後想知道「誰在吃空間」就一行重跑，不必每次重想要比對哪些目錄、要怎麼處理命名差異。腳本和 `disk-report` 收在同一個公開 repo [tarrragon/scripts](https://github.com/tarrragon/scripts) 裡，維持「跟專案無關的系統工具放個人 bin」的一致做法。

兩支腳本在同一個 repo；若已為 `disk-report` clone 過 `~/Projects/scripts`，跳過 clone、只做 symlink。首次安裝則把 repo clone 下來，再把腳本本體 symlink 到個人的 `~/.local/bin`，這樣本機呼叫的永遠是 repo 的最新版：

```bash
git clone https://github.com/tarrragon/scripts.git ~/Projects/scripts
ln -s ~/Projects/scripts/app-report/app-report ~/.local/bin/app-report
```

PATH 設定同 disk-report（見 [macOS 新機基礎建設](../macos_new_machine_setup/)）。裝好後直接呼叫：

```bash
app-report           # 完整報告：App 聚合排行 + Developer + Homebrew
app-report --apps    # 只看 App 聚合排行（預設前 30）
app-report --apps 50 # 排行顯示前 50
app-report --dev     # 只看 ~/Library/Developer 開發工具共用資料
app-report --brew    # 只看 Homebrew
```

要清哪個 App，看完明細再動手：移掉 `.app` 並清對應的 `~/Library` 資料夾（報告每個 App 下方列的路徑就是清除對象；先從 `Caches` / `HTTPStorages` 開始，確認再考慮資料目錄），Homebrew 用 `brew cleanup -s`。

## 兩支腳本的分工

`disk-report` 與 `app-report` 是磁碟清理的兩個接力棒。前者在卷與目錄層找出最大的子樹，通常落在 `~/Library`；後者接手把那棵子樹拆到 App，看出具體是誰佔的、各自有多少是可清的快取。先 disk 找方向、再 app 定位到人，兩支都唯讀，回收的最後一步都留在人這一端。
