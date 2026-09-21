---
title: "Ring Buffer（環狀緩衝區）"
date: 2026-09-21
description: "撈 log 撈不到事發當下那幾行、或想知道一份 log 能回溯多久時讀 — 固定大小、寫滿之後從頭覆蓋的紀錄區"
weight: 22
tags: ["dotfile", "linux", "logging", "debugging"]
---

環狀緩衝區是一塊固定大小的紀錄區，寫到底之後折回開頭覆蓋最舊的內容。核心的訊息（`dmesg` 讀的那一份，[OOM killer 殺掉程序](/linux/dotfile/knowledge-cards/oom-exit-code-137/)的紀錄就住在那裡）與 Android 的 `logcat` 都用這個結構，理由是它的記憶體用量有上界，不會因為某個服務話多就把磁碟寫滿。

## 概念位置

相關概念：[systemd OnFailure](/linux/dotfile/knowledge-cards/systemd-onfailure/)（服務失敗時的告警路徑，與事後翻 log 互補）、[OOM Killer 與退出碼 137](/linux/dotfile/knowledge-cards/oom-exit-code-137/)（核心訊息裡最常被回溯的一類事件）。讀取工具與各自的權威來源見[日誌閱讀與診斷工具](/linux/dotfile/07-desktop-maintenance/log-reading-diagnostic-tools/)。

## 它能回溯多久由寫入速率決定，不由時間決定

固定大小加上持續寫入，推出一個對排查影響很大的性質：**這份紀錄能回溯的時間長度是浮動的**。同一個緩衝區在安靜的機器上存得住好幾天，在一台常駐服務很多的機器上可能只有幾分鐘。POS 機、車機、跑著多個背景同步的開發機都落在後面那一類。

所以「撈不到那幾行」有兩種成因而它們長得一樣：那件事沒有發生，或者它發生過而已經被覆蓋掉了。零筆結果本身不構成證據，要先確認事發時間還在緩衝區涵蓋的範圍內。

## 取事發當下那幾行的做法是先界定範圍

緩衝區自己就是收集器，所以不需要一個從頭跑到尾的收集程序。做法是用它的兩端界定範圍——清空劃下起點、倒出劃下終點，中間那一段就是重現問題的時候裝置自己寫進去的：

```bash
logcat -G 16M    # 放大（Android）
logcat -c        # 清空，起點
# ...重現問題...
logcat -d        # 倒出，終點
```

放大要在清空之前做，因為改變大小通常會把現有內容丟掉。核心那一份（`dmesg`）的大小由開機參數 `log_buf_len` 決定，執行中改不了，所以那一份只能事後讀、不能事前放大。

## 與 journald 的差別

`systemd-journald` 不是環狀緩衝區：它寫的是磁碟上的檔案，靠 `SystemMaxUse` 這類設定與輪替來限制總量，所以它的紀錄跨得過重開機，而環狀緩衝區的內容開機就沒了。查一件昨天發生的事該去 journal，查一件剛剛發生而且與核心或裝置有關的事該去環狀緩衝區——兩者涵蓋的時間範圍不同，選錯會得到一個空結果而不是一則錯誤。

Android 沒有 journald，`logcat` 就是全部，所以那個平台上「事後才想到要看 log」的成功率明顯較低，值得在操作之前就先把範圍界定好。完整的參數與篩選做法見 [adb 遠端診斷 Android 實機](/work-log/adb-remote-android-diagnosis/)。
