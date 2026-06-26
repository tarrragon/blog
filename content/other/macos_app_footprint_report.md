---
title: "macOS 每個 App 到底吃多少空間：聚合佔用的 app-report 腳本"
date: 2026-06-27
description: "disk-report 能找出 ~/Library 是大戶，卻答不出那是哪些 App 的。這篇記錄一個把每個 App 散落在 ~/Library 各處的佔用聚合成單一數字的 app-report 腳本，以及為什麼 .app 的大小會嚴重低估真實佔用。"
tags: ["macos", "disk-space", "tooling", "homebrew", "troubleshooting"]
---

`du ~/Library/*` 只能告訴你 Caches、Containers 這些目錄各佔多少，答不出「Steam 這個 App 一共吃了多少」。原因是一個 App 的資料散落在 `~/Library` 好幾個不同位置，按目錄統計就拆不回它名下。這篇記錄一個把這些散落佔用聚合回各 App 的 `app-report` 腳本。它和磁碟層的 [disk-report](../macos_disk_space_diagnosis/) 是一組：後者找出哪棵子樹最大，這篇把子樹拆到 App。

## 一個 App 的真實佔用不等於它的 .app 大小

判斷一個 App 吃多少空間，要算的是它的總足跡（footprint），而不是 `/Applications` 裡那顆 `.app` 的大小。`.app` 只是程式本體，App 跑起來產生的資料（下載內容、快取、登入狀態、設定、日誌）絕大多數寫在 `~/Library` 底下的好幾個不同位置，跟 `.app` 完全分家。

這台機器上最極端的例子是 Steam：它的 `.app` 只有 10.8M，但遊戲資料佔了 8.1G，兩者差了近 800 倍。只看 `/Applications` 的大小排序，Steam 會排在很後面，完全看不出它是全機第一大戶。同樣地，Amazon Kindle 的 `.app` 才 138M，書庫卻在沙箱容器裡佔了 3.2G。這就是為什麼「按目錄統計」和「按 App 統計」會給出完全不同的排行；要回答「哪個 App 該清」，必須把佔用聚合回 App。

## 佔用散落在 ~/Library 的哪些地方

聚合的第一步是知道一個 App 會把資料寫到哪些固定位置。macOS 對這些位置有約定，每個位置承擔不同責任，也決定了它能不能安全清掉。

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

所以腳本對每個 App 先讀出它的 bundle id，然後 `Caches`、`Application Support`、`Logs` 這幾個位置兩種命名都比對一次，bundle id 專屬的位置（`Containers`、`HTTPStorages`、`Saved Application State`）則用 bundle id 找。`Group Containers` 又是另一種格式，名稱前面多一段開發商的 team id（10 碼英數，像 `ABCDE12345.group.com.foo`），所以改用 bundle id 做子字串比對。這套規則涵蓋了絕大多數 App，但用罕見自訂命名的資料仍可能漏抓，這是聚合式估算的固有邊界，腳本在輸出裡據實標明「可能漏抓」而不假裝是精確值。

## Homebrew 要分開算

透過 Homebrew 裝的工具不在 `/Applications`，所以要獨立統計。它的佔用集中在自己的目錄樹底下，分兩類：命令列工具與函式庫（formula）在 `Cellar/`，GUI App 與二進位（cask）在 `Caskroom/`。

這台機器的 formula 前幾名是開發語言執行環境：`dotnet@9` 634M、兩個版本的 `openjdk` 合計 600M、`mysql` 292M、`go` 258M。formula 會多版本並存（例如 `python@3.13` 和 `python@3.14` 各算各的），所以腳本把整個 formula 目錄一起計。除了已安裝的部分，腳本還列出 `brew --cache` 的下載快取，以及 `brew cleanup -n` 預估可回收的舊版本（`-n` 是 dry-run，只報告不刪），跟整支腳本的唯讀原則一致。

## 聚合一律用 du 取實際佔用

App 各位置的聚合一律用 `du -skx` 取實際佔用，而不是 `ls` / `find -size` 的邏輯大小。為什麼 sparse 檔讓這個選擇變成必要，[disk-report 那篇](../macos_disk_space_diagnosis/)已經拆解過；放到 App 聚合的脈絡，關鍵是容器與資料目錄裡正好常有 VM 映像、容器磁碟這類 sparse 檔，它們的邏輯大小動輒是實際佔用的數十倍，拿來加總會把整份聚合排行灌水。

`-x` 讓 `du` 不跨越檔案系統邊界，避免把掛載進來的卷重複計入；`-k` 統一用 KB 當單位，方便把各位置的數字加總後再換算成人類可讀的 G / M。

## 實測結果

下面是這台機器跑出來的排行，App 與數字都是單機實測、你的會完全不同；要看的是聚合排行和「按目錄統計」給的印象差多少：

| App           | 總佔用 | 主要落點                             |
| ------------- | ------ | ------------------------------------ |
| Steam         | 8.1G   | data 8.1G（`.app` 只有 10.8M）       |
| Xcode         | 4.8G   | bundle 4.8G                          |
| Readmoo 看書  | 4.6G   | data 3.8G + bundle 816M              |
| Dia           | 4.1G   | cache 1.6G + bundle 1.3G + data 1.1G |
| Amazon Kindle | 3.3G   | container 3.2G（`.app` 才 138M）     |

全機掃到 65 個 App、聚合總計 48.2G。這份排行的價值在於它直接指向「該從哪裡下手」，而判讀邏輯可以套到任何人的排行上：本體小、資料大的 App（這台是 Steam、Kindle）要回收就得處理書庫與遊戲本身；純快取大的（這台是 Dia 的 1.6G）清掉零風險；本體就大的開發工具（Xcode、Android Studio）除非不再開發否則動不得。同一個總數字底下，可清的比例天差地別，這正是逐項明細要回答的問題。

## 固化成 app-report 腳本

把這套聚合邏輯寫成腳本，往後想知道「誰在吃空間」就一行重跑，不必每次重想要比對哪些目錄、要怎麼處理命名差異。腳本和 `disk-report` 收在同一個公開 repo [tarrragon/scripts](https://github.com/tarrragon/scripts) 裡，維持「跟專案無關的系統工具放個人 bin」的一致做法。

安裝方式是把 repo clone 下來，再把腳本本體 symlink 到個人的 `~/.local/bin`，這樣本機呼叫的永遠是 repo 的最新版：

```bash
git clone https://github.com/tarrragon/scripts.git ~/Projects/scripts
ln -s ~/Projects/scripts/app-report/app-report ~/.local/bin/app-report
```

這一步預設 `~/.local/bin` 已在 PATH 上。若還沒設定，做法見 [macOS 新機基礎建設](../macos_new_machine_setup/) 的對應項目。裝好後就能直接呼叫：

```bash
app-report           # 完整報告：App 聚合排行 + Homebrew
app-report --apps    # 只看 App 聚合排行（預設前 30）
app-report --apps 50 # 排行顯示前 50
app-report --brew    # 只看 Homebrew
```

腳本和 `disk-report` 一樣刻意設計成唯讀，只統計、不刪任何東西。要清哪個 App，看完明細再動手：移掉 `.app` 並清對應的 `~/Library` 資料夾，Homebrew 用 `brew cleanup -s`。報告的工作是讓「可清的快取」和「動不得的資料」一目了然，刪不刪由人定。

## 兩支腳本的分工

`disk-report` 與 `app-report` 是磁碟清理的兩個接力棒。前者在卷與目錄層找出最大的子樹，通常落在 `~/Library`；後者接手把那棵子樹拆到 App，看出具體是誰佔的、各自有多少是可清的快取。先 disk 找方向、再 app 定位到人，兩支都唯讀，回收的最後一步都留在人這一端。
