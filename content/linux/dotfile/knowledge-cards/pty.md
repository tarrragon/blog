---
title: "PTY（Pseudo-Terminal，虛擬終端機）"
date: 2026-09-21
description: "二進位資料經過某條通道之後壞掉、或程式在管線裡與在終端機裡行為不同時讀 — 核心提供的一對虛擬終端機裝置"
weight: 21
tags: ["dotfile", "linux", "tty", "terminal"]
---

PTY（pseudo-terminal）是核心提供的一對虛擬裝置：一端交給要被操作的程式、另一端交給操作它的人或程式，而被操作的那一端以為自己接在一台真實終端機上。[TTY](/linux/dotfile/knowledge-cards/tty/) 是核心直接提供的實體文字終端機，PTY 則讓使用者空間的程式（終端機模擬器、SSH、`adb shell`、`tmux`）自己扮演終端機那一側。

## 概念位置

相關概念：[TTY](/linux/dotfile/knowledge-cards/tty/)（核心的實體文字終端機）、[SIGHUP](/linux/dotfile/knowledge-cards/sighup-hangup-signal/)（主控端關閉時核心送出的訊號）、[終端 CJK 雙寬字與即時輸入](/linux/dotfile/knowledge-cards/terminal-cjk-input/)（raw 模式與行規則的另一組後果）。

一對 PTY 分成主控端與從屬端。從屬端在檔案系統上長得像一個終端機裝置，程式對它做的每一件事——判斷自己是不是接在終端機上、要不要開彩色輸出、要不要行緩衝——結果都與接上實體終端機時相同。主控端拿到的是另一頭的位元組流，終端機模擬器把它畫成視窗裡的字，SSH 把它送到網路另一端。

## 經過 PTY 的位元組會被加工

核心對穿過 PTY 的資料套用**行規則**（line discipline），那是終端機該做的事：把輸入回顯給使用者看、把 `Ctrl+C` 翻譯成訊號、緩衝整行直到按下 Enter，以及輸出端的換行轉換——把 `0x0A` 補成 `0x0D 0x0A`。

這些加工對文字是便利，對二進位資料是破壞。PNG、tar、gzip 的內容裡 `0x0A` 是資料而不是行尾，被轉換過的每一處都讓檔案的長度與內容一起偏移，而整個過程不產生任何錯誤訊息。判讀的訊號是**檔案比預期大，多出來的位元組數等於原始資料裡 `0x0A` 的個數**。

所以要取二進位輸出的時候，選的是不經過 PTY 的路徑。`ssh` 帶 `-T`、`adb` 用 `exec-out` 而不是 `shell`、`docker exec` 不帶 `-t`，走的都是同一個判斷。實例與逐項驗證見 [adb 遠端診斷 Android 實機](/work-log/adb-remote-android-diagnosis/)。

## 什麼時候會配置 PTY

配置與否由呼叫端決定，而預設值隨工具而異：互動式登入一定配置（否則沒有回顯與訊號），帶命令直接執行的多半不配置。多數工具給得出旗標覆寫它——`ssh -t` 強制配置、`ssh -T` 強制不配置、`adb shell -tt`、`docker exec -t`。

判斷手上這條通道有沒有配置，最短的方法是送一段已知的位元組回來看它有沒有被改：

```bash
<遠端執行指令> "printf 'a\nb\n'" | xxd
# 610a 620a        沒有配置
# 610d 0a62 0d0a   配置了
```

程式自己也看得到這件事——`test -t 1` 判斷標準輸出是不是終端機，許多工具據此決定要不要輸出顏色，這是同一個指令在終端機裡有色、導進檔案後沒色的原因。

## 主控端關閉會送出 SIGHUP

主控端被關掉的時候，核心對從屬端的前景程序群組送出 [SIGHUP](/linux/dotfile/knowledge-cards/sighup-hangup-signal/)，預設處置是結束程序。SSH 連線斷掉時，直接在那條連線上啟動的工作活不過斷線，走的就是這條路徑，而 `tmux` 與 `screen` 解決它的方式是自己持有一對 PTY——真正的工作接在那一對上，使用者的連線斷掉時被關掉的是使用者那一端，工作那一端的主控端還在 `tmux` 手上。
