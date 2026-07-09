---
title: "平台與發行版差異的判讀地圖"
date: 2026-07-02
description: "跨 macOS / Linux 或跨發行版寫 bootstrap、某個 app 在 ARM/aarch64 裝不起來、或除錯時不確定該用哪個工具與套件名時回來讀"
weight: 8
tags: ["linux", "bootstrap", "package-manager", "cross-platform"]
---

同一個工作環境要在多台機器上復現時，差異集中在四個層次：套件管理器、套件名稱、套件存在性、版本節奏。這四層決定了 bootstrap 腳本哪些部分能共用、哪些必須按平台獨立維護，也決定了除錯時要先確認自己站在哪個平台上——很多「工具行為不對」的問題，根因是把 A 平台的經驗直接套到 B 平台。

## 差異的四個層次

### 套件管理器：每個平台各有原生解

macOS 用 Homebrew、Arch 用 pacman、Debian/Ubuntu 用 apt、Fedora 用 dnf。安裝指令、確認旗標、資料庫同步模型都不同，其中兩個差異會直接咬到自動化腳本：

- **非互動旗標不對稱**：apt 的慣例是 `-y`，pacman 是 `--noconfirm`。腳本只寫了其中一邊，換平台就會卡在確認提示——非 TTY 環境下（SSH 一行式、CI、無人值守）沒人回答 `[Y/n]`，pacman 直接以錯誤結束。
- **資料庫同步模型不同**：Arch 是 rolling release 且鏡像不保留舊版檔案，裝機當下的套件資料庫幾天內就會指向已被輪替掉的檔名，安裝時收到 404（`failed retrieving file`）。修法是安裝前先 `pacman -Syu` 同步資料庫並全系統升級——只 `-Sy` 不 `-u` 會造成 partial upgrade（新資料庫裝新套件、舊系統缺新依賴）。Debian stable 的套件庫凍結、沒有這個時序問題，但代價是版本舊。

### 套件名稱：同一個工具、各發行版各叫各的

| 工具            | Arch             | Debian/Ubuntu                  | Fedora                       |
| --------------- | ---------------- | ------------------------------ | ---------------------------- |
| fd              | `fd`             | `fd-find`（執行檔叫 `fdfind`） | `fd-find`                    |
| bat             | `bat`            | `bat`（執行檔叫 `batcat`）     | `bat`                        |
| gh              | `github-cli`     | `gh`                           | `gh`                         |
| CJK 字型        | `noto-fonts-cjk` | `fonts-noto-cjk`               | `google-noto-sans-cjk-fonts` |
| Meslo Nerd Font | `ttf-meslo-nerd` | 未打包（手動裝）               | 未打包                       |

Debian 的重命名還會連執行檔一起改（`fdfind`、`batcat`），所以連 shell alias 與腳本內的指令呼叫都要跟著分歧。維護跨發行版清單的可靠做法是逐台實測建立——憑印象抄一份對照表，漂移只是時間問題。

跨到 macOS 還有一個 Linux 之間看不到的軸：**BSD userland vs GNU coreutils**。macOS 的基礎工具是 BSD 版，很多腳本習慣用的 GNU 工具在 macOS 預設根本沒有（不是改名、是缺席）：`timeout` 就是一例——實測一支腳本硬編 `timeout` 在 macOS 直接 `command not found`。裝了 Homebrew 的 `coreutils` 會補上 GNU 版、但一律加 `g` 前綴（`gtimeout`、`gsed`、`gdate`、`greadlink`），不覆蓋 BSD 原生。更陰險的是同名還在、行為卻不同：`sed -i` 要接一個備份後綴參數（BSD）vs 不用（GNU）、`readlink -f`（GNU）BSD 沒有、`date` 的旗標各異。跨 macOS 的腳本要嘛偵測 `gtimeout` / `timeout` 擇一（都沒有就略過那層保護），要嘛只用兩邊都有的 POSIX 子集。這個軸逐工具的差異與對策（含 `sed -i`、`readlink -f`、bash 3.2）見 [macOS 的 BSD userland](/macos/macos_bsd_userland_vs_gnu/)。

### 套件存在性：有些概念只存在於特定平台

Hyprland 在 Arch 官方 repo、Fedora 要 COPR、Debian stable 沒有；[Quickshell](/linux/dotfile/knowledge-cards/quickshell/) 只有 Arch 打包。反過來，macOS 的 cask app（GUI 應用程式）概念在 Linux 對應的是各桌面環境自己的生態。這層差異沒有翻譯的空間——桌面層的清單是平台專屬的維護對象。

存在性差異還有一個容易漏看的軸：**CPU 架構**。發行版 repo 有這個工具、不代表它在你的架構上存在——尤其是專有軟體的二進位發行。實測案例：Arch aarch64（ALARM）的 repo 有 `spotify-launcher`（工具本身有 aarch64 建置），但它要下載的 Spotify 官方 client 只發 x86_64/i386 deb，實跑直接回報 `There are no packages for your cpu's architecture (cpu="aarch64", supported=["amd64", "i386"])`。這類失敗的判讀重點是分清「工具沒打包」跟「工具打包了、它依賴的專有 blob 沒有這個架構」——前者可能有 [AUR](/linux/dotfile/knowledge-cards/aur/)（Arch 社群自建套件庫）/ 第三方 repo 補、後者只能找替代路徑（Spotify 的替代是 Web Player + 從 ChromeOS 鏡像抽出的 arm64 Widevine CDM）。DRM、GPU driver、印表機 driver 這類含專有二進位的軟體，在非 x86_64 架構上都要先查架構支援再排進安裝清單。

### 版本節奏：rolling 與 stable 的行為差

Arch rolling 永遠最新，Debian stable 的同名工具可能舊兩年。版本差會讓 config 語法對不上（新版工具的設定選項在舊版不存在）、也會讓「照著文件做卻失敗」——文件寫的是新版行為。除錯時看到「同一份 config 在 A 機器能跑、B 機器報錯」，先比對兩邊的工具版本再懷疑 config 本身。

## 除錯前先定平台

跨平台差異對除錯的意義：**判讀工具與修法都是平台相依的，先確認自己站在哪，再開始查。** 三條指令建立座標：

```bash
cat /etc/os-release        # 發行版與版本（Linux）
uname -m                   # CPU 架構：x86_64 / aarch64（套件生態差很多）
command -v pacman apt-get dnf brew   # 哪個套件管理器在場
```

架構那條容易被忽略：aarch64（ARM）的套件生態比 x86_64 小——Homebrew on Linux 對 aarch64 的預編譯 bottle 覆蓋率偏低（截至撰稿仍屬 tier-2 支援、多數要現場編譯）、AUR 部分套件不支援 ARM。在 ARM 機器上照 x86 的教學走，會在意想不到的地方碰壁。

## Bootstrap 的分歧設計判準

把差異收進腳本架構的三條判準，決定每段邏輯住在哪：

1. **安裝手段跨平台一致**（git clone、curl installer、stow 部署）→ 進共通層，一份邏輯全平台用
2. **只是套件名或套件管理器不同** → 各平台一份安裝腳本 + 一份套件清單，獨立維護、分歧不寫進共通層的 if/else
3. **概念只存在於某平台**（Hyprland、cask）→ 只出現在該平台清單的桌面層

這個切法的維護成本結構：共通層改一次全平台生效；平台層只在你真的用那個平台時才付維護成本。沒有實測機器的發行版不預先建清單——那種清單沒有實測支撐、注定漂移。

## 統一層的誘惑與代價

「用一個跨平台套件管理器統一所有機器」聽起來能消掉整個分歧層，實際的適用邊界很窄。Homebrew 支援 Linux，但它在 Arch 上會建一套與 pacman 平行的套件世界（獨立 prefix、重複的函式庫、PATH 互搶），而且對 aarch64 Linux 的 bottle 覆蓋率低（截至撰稿）、缺 bottle 的套件要現場從原始碼編譯。它真正的適用場景是「發行版套件太舊」（如 Ubuntu LTS 上要新版工具）或「沒有 root 權限」。Nix 能做到真正的跨平台一致，代價是整套心智模型重學。判準是：分歧層的維護成本（每個發行版一份清單）低於統一層的引入成本時，保持原生套件管理器 + 分平台清單。

## 下一步路由

- Bootstrap 腳本本身的設計（log 落地、錯誤定位）見[可除錯的 bootstrap](/linux/install/observable-bootstrap/)
- 最小系統缺什麼、怎麼驗證見[最小安裝後的工具驗證與補足](/linux/install/minimal-install-verify/)
- 出問題時的判讀紀律見 [Linux 除錯與診斷](/linux/debug/)
- dotfile repo 怎麼同時服務 macOS 與 Linux 見[一個 repo 管理跨平台環境](/linux/dotfile/01-dotfile-management/cross-platform-one-repo/)
