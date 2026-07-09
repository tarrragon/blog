---
title: "macOS 的 BSD userland：GNU 習慣在這裡會撞的地方"
date: 2026-07-09
description: "指令或腳本在 Linux 好好的、搬到 macOS 卻 command not found 或行為不同（timeout、sed -i、readlink -f、bash 語法），想搞懂 macOS 的命令列工具為何跟 Linux 不一樣、怎麼繞時回來讀"
tags: ["macos", "bash", "shell", "coreutils", "tooling", "cross-platform"]
---

macOS 的命令列 userland 是 BSD 系、不是 GNU。你在 Linux 養成的 GNU 工具習慣（GNU coreutils、較新的 bash）搬到 macOS 會在三個地方撞牆：工具根本不在、同名但行為不同、bash 版本太舊。這篇講的是同一個底層事實的三種表現——理解「macOS 給的是 BSD、加上被凍結的舊 GNU」這一件事，就能預期並繞過這些差異，而不是每撞一次查一次。

## 為什麼是 BSD、而且是舊的 GNU

macOS 的 Unix 底子（Darwin）來自 BSD，所以內建的命令列工具是 BSD 版，語意跟旗標跟著 BSD。至於 GNU 版本的工具，Apple 刻意停在舊版：GNU 的 coreutils、bash 等專案在某個時點把授權從 GPLv2 改成 GPLv3，而 GPLv3 的專利與反 Tivoization 條款是 Apple 不接受的，於是 Apple 把系統內建的 GNU 工具凍在最後一版 GPLv2、之後不再更新，整體改倚重 BSD 與自家工具。`/bin/bash` 停在 3.2（2007 年的版本）就是這個決定最顯眼的標記。

結論是：macOS 給你的是「BSD userland + 一套凍結在多年前的舊 GNU」。這不是缺陷或沒維護，是授權取捨下的刻意設計。知道成因，下面三種現象就都是可預期的。

## 形態一：工具根本不在

GNU-only 的工具在 macOS 預設沒有，呼叫直接 `command not found`。最常撞的是 `timeout`（GNU coreutils 的一員）——一支在 Linux 用 `timeout 60 some-cmd` 包起來的腳本，搬到 macOS 第一步就掛。

判讀很直接：一個在 Linux 上理所當然的指令，在 macOS 回 `command not found`，先問「它是不是 GNU coreutils / GNU-only 的東西」。是的話，macOS 本來就沒有，要嘛裝（見下方對策）、要嘛換不依賴它的寫法。

## 形態二：同名、行為不同（最陰險）

比「工具不在」更難抓的是工具名一樣、但 BSD 版的旗標或語意跟 GNU 版不同——它不報錯，默默做出不一樣的結果。幾個天天會用到的：

- **`sed -i`**：BSD 版的 `-i` 後面**必須**接一個備份檔後綴（`sed -i '' 's/a/b/' file` 那個空字串就是「不留備份」）；GNU 版的 `-i` 直接就地改、不接參數。把 GNU 寫法 `sed -i 's/a/b/' file` 搬到 BSD，`sed` 會把 `s/a/b/` 當成備份後綴、把 `file` 當成 script，行為全錯。
- **`readlink -f`**：解析符號連結的最終絕對路徑，GNU 有這個旗標，BSD 版長年沒有（macOS 較新版本才補上）。可攜的替代是 `realpath`，或退回不依賴它的方式。
- **`date`**：算日期時間 GNU 用 `date -d '...'`、BSD 用 `date -v`（相對）或 `date -j`（指定），旗標完全不同，照抄必錯。
- **`stat` / `grep -P` / `find` / `xargs`**：`stat` 的格式旗標 GNU 是 `-c`、BSD 是 `-f`；`grep -P`（PCRE）GNU 有、BSD 沒有；`find`、`xargs` 也有零星旗標差異。

這一類的判讀訊號是「腳本沒報錯、但輸出或副作用跟預期不同」。看到跨平台腳本在 macOS 上結果怪，先懷疑用到的是哪個 BSD/GNU 行為分歧的指令。

## 形態三：bash 太舊，而且預設 shell 已換

`/bin/bash` 凍在 3.2，所以 bash 4 以後才有的語法在 macOS 的系統 bash 上全部不存在：關聯陣列（`declare -A`）、`${var,,}` / `${var^^}` 大小寫轉換、`readarray` / `mapfile`、`|&`。一支 `#!/bin/bash` 又用了這些的腳本，在 macOS 會直接語法錯。

另外 macOS 的**預設互動 shell 已經是 `zsh`**（從 Catalina 起），bash 要自己裝。所以「假設使用者的 shell 是 bash」這件事在 macOS 也不成立。

順帶一個 locale 相關、跨平台都可能但 macOS 預設設定容易踩的坑：非 UTF-8 locale 下，shell 變數 `$var` 後面若緊跟一個多位元組字（例如中文全形括號），bash 可能把該字的首位元組吞進變數名、報 unbound。寫法上一律用 `${var}` 把變數名邊界標清楚就能免疫。

## 對策與取捨

三條路，依「這支腳本要給誰跑」選：

- **裝 GNU 工具（自己的互動環境）**：`brew install coreutils gnu-sed findutils grep gawk bash`。`coreutils` 裝的是 **g-prefix** 版（`gtimeout`、`gsed`、`greadlink`、`gdate`），刻意不覆蓋 BSD 原生——因為系統與其他軟體可能依賴 BSD 行為，覆蓋會弄壞它們。要讓無前綴的名字也走 GNU 版，把 `$(brew --prefix)/opt/coreutils/libexec/gnubin` 加進 PATH（那裡有無前綴的 symlink 指向 GNU 版）。但這會讓你的 shell 跟系統其他部分的 BSD 假設分歧，所以只在自己的互動環境加、別設成全域或寫進要交付的腳本。新 bash 裝到 `/opt/homebrew/bin/bash`，腳本要用 `#!/usr/bin/env bash`（走 PATH）才抓得到它，`#!/bin/bash` 仍是系統的 3.2。
- **只寫 POSIX 子集（要兩邊都跑的腳本）**：避開所有 GNU-ism——`sed -i` 改用 tmp 檔加 `mv`、不用 `readlink -f`（用 `realpath` 或 `cd && pwd`）、不用關聯陣列。最可攜、macOS / Linux / BSD 都動，代價是放棄 GNU 的便利語法。bootstrap 腳本、CI 腳本適用。
- **偵測分支（有就用、沒有就退化）**：`command -v gtimeout >/dev/null && T=gtimeout || { command -v timeout >/dev/null && T=timeout || T=""; }`，用 `$T` 呼叫、空的就略過那層保護。給「這個工具是加分、缺了不致命」的用法。

判準是：自己天天用的互動環境，裝 `gnubin` 圖方便沒問題；但**要交付給別人或 CI 跑的腳本，不能假設對方裝了 GNU 工具**——那種要嘛 POSIX 子集、要嘛偵測分支。把「我的機器剛好裝了 coreutils」當成腳本的前提，就是這篇一開始那些跨平台故障的來源。

## 下一步路由

- 一台新 Mac 從開箱到能開發、Homebrew / bash / 個人 bin 的設定順序：[新機基礎建設](../macos_new_machine_setup/)
- 跨 Linux 發行版與 macOS 的工具名、存在性、版本節奏分歧全景：[平台與發行版差異的判讀地圖](/linux/install/platform-divergence-map/)
- 寫跨平台 bootstrap 腳本時「別硬編你這台剛好有的東西」（權限、工具、locale）：[bootstrap 腳本的骨架與套件清單](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)
