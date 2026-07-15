---
title: "乾淨機器驗證：repo 宣告了什麼、機器實際依賴什麼"
date: 2026-07-15
description: "覺得 dotfile 已經『可重現』、或想確認 install.sh 換一台新機器真的跑得起來時回來讀"
weight: 4
tags: ["dotfile", "workflow", "可重現性"]
---

Dotfile repo 記錄的是**宣告**——環境應該長什麼樣（見 [Dotfile 是重建指令，不是備份](/linux/dotfile/00-dotfile-mindset/dotfile-iac-parallel/)）。但一台用了很久的工作機，實際依賴的狀態往往比 repo 宣告的更多。這兩者的差額，就是「以為可重現、其實不然」的來源。驗證這個差額的唯一工具，是在一台沒有累積狀態的乾淨機器上、把 `install.sh` 實跑一遍——不是讀 repo 確認「看起來有寫」。

## 宣告 vs 實際依賴

讀 repo 只顯示宣告了什麼。它在結構上看不見「機器實際依賴、但 repo 沒宣告」的部分——因為那些依賴根本不在 repo 裡，無從讀起。

實際依賴散落在 repo 追蹤不到的地方：

- **安裝器寫進非-repo 追蹤的 shell profile**。裝 Homebrew、rustup、nvm、conda 這類工具時，安裝器常會在 `~/.bashrc`、`~/.zprofile`、`~/.profile` 尾端 append 一行 PATH 或 init。如果 dotfile 沒把這些 profile 收進 repo（或沒在自己管理的 `env.zsh` 重新宣告），新機器上工具裝了、shell 卻找不到（見 [PATH 的集中宣告](/linux/dotfile/02-shell-config/path-plugin-prompt/)）。
- **系統層的 PATH drop-in**。官方 `.pkg` / 套件會丟 `/etc/paths.d/`（macOS）或 `/etc/profile.d/`（Linux）的檔案來設 PATH。這些是系統檔、不在家目錄的 dotfile 範圍，重灌後不會自己回來。
- **手動裝過、忘了它存在的 runtime**。幾個月前手動裝的 Go、Node、Python 就在機器上，於是 bootstrap 從沒被迫處理「這台沒有 runtime」的情況。
- **來源寄居在別專案的工具**。一個全域使用的 CLI，來源目錄卻在某個別專案的 checkout 裡（`~/project/foo/tools/bar`）。換機器那個專案不在，工具就裝不回來——重建鏈斷在那個 checkout。

## 原機是一台被污染的儀器

一台工作機的狀態只增不減，而且從不標示哪些是承重的。每次手動安裝、每個編輯 profile 的 installer、每個指向本地目錄的工具，都加進一條 repo 不知道的依賴。

因此「在原機上驗證 dotfile 可不可重現」本身是矛盾的：原機正是累積了所有這些未宣告狀態的機器，它偵測不到自己的污染。讀 repo「看起來很完整」的那種完整感，來自原機把缺口補起來了——換一台乾淨機器，那些補丁全部消失。

## 怎麼驗：乾淨機器實跑

驗證要在一台沒有累積狀態的機器上跑，且要跑真正宣告的步驟：

1. **乾淨 = 沒有任何累積狀態**：全新 VM、拋棄式 container、或全新使用者帳號——不是原機、也不是用過的機器。涵蓋目標作業系統（見 [可觀測的 bootstrap](/linux/dotfile/08-sync-bootstrap/) 對「要在真正乾淨、且涵蓋目標 OS 的環境各跑一次」的展開）。
2. **跑真實的 install，不是讀 repo、也不是心裡走一遍**：靜態檢視跟原機共享同一組盲點——它看得到宣告，看不到缺的依賴。
3. **每個失敗都是一條未宣告的依賴**：乾淨機器跟預期分歧的每一個點，都指出一條 repo 漏掉的狀態。把它搬進 repo（收進 dotfile、或在 `install.sh` 補上），或明確標成刻意手動。產出不是「通過了」，是「原本沒被意識到的依賴清單」。
4. **驗證用的乾淨機器跑過一次就被污染了**：有意義的重跑之間要重置（VM 還原快照、container 重建）。

這條紀律的定期版本：每隔一段時間在拋棄式環境跑一次完整 bootstrap，確認這份重建指令真的還能重建（見 [同步策略與機密處理](/linux/dotfile/08-sync-bootstrap/sync-strategy-secret/)）。

## 判讀訊號

| 訊號                                                   | 該做的事                                                                 |
| ------------------------------------------------------ | ------------------------------------------------------------------------ |
| 宣稱 dotfile 可重現、但只在自己機器上驗過              | 在乾淨機器實跑一次才算數——原機驗不出缺口                                 |
| 某個工具「這台能用、換機器就 command not found」       | 找那條 repo 沒記錄、原機卻存在的狀態（profile / drop-in / 手裝 runtime） |
| 安裝器印出「請把這行加進 ~/.bashrc」而 install.sh 沒做 | 那步就是未宣告依賴——收進 dotfile 或在 script 內補上                      |
| 工具的來源指向某個別專案的目錄                         | 換機器就裝不到——來源要提成可重現的 spec 或標成手動                       |
| 讀 repo / 跑 lint 都「看起來完整」                     | 完整感來自原機污染——換乾淨機器實跑才是真檢查                             |

這條原則的工程檢討版（跨平台、非 dotfile 專屬）見 [報告 #227：可重現性只有乾淨機器重跑才驗得出](/report/clean-room-reproduce-reveals-non-repo-state/)。
