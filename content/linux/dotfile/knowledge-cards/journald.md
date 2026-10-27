---
title: "journald（systemd-journald）"
date: 2026-10-26
description: "用 journalctl 查不到重開機之前的紀錄、journal 佔掉多少磁碟不清楚、某個服務的 log 出現 Suppressed 訊息，或要判斷一筆紀錄該去 journal 還是 /var/log 底下的檔案找時"
weight: 56
tags: ["dotfile", "linux", "systemd", "logging", "knowledge-cards"]
---

journald（程式名是 `systemd-journald`）是 systemd 的紀錄收集服務：每個 systemd 服務寫到標準輸出與標準錯誤的內容、程式經由 syslog 介面送出的訊息、核心的訊息，都由它收下，加上服務名、程序 ID、開機編號、時間這些欄位，存成二進位的 journal 檔，再用 `journalctl` 依欄位查詢。它跟 [Ring Buffer（環狀緩衝區）](/linux/dotfile/knowledge-cards/ring-buffer-log/) 的差別在儲存：環狀緩衝區是固定大小、寫滿覆蓋的記憶體區塊，journald 寫的是檔案，靠設定的上限刪掉最舊的檔案。

## 概念位置

journald 在一台主機的紀錄來源裡是預設的那一份：用 systemd 管的服務不必自己寫 log 檔，輸出就進了 journal。有裝 rsyslog 的發行版（Oracle Linux、RHEL 是這一種）另外從 journald 轉出一份文字檔到 `/var/log/messages`、`/var/log/secure`，這兩份文字檔由 [logrotate](/linux/dotfile/knowledge-cards/logrotate/) 輪替，journal 本身不經過 logrotate。長期上線的主機上 journal 存在哪裡、上限多少、要讀哪些欄位，見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/devops/operations/09-host-lifecycle/long-running-host-maintenance/)〈journald 的紀錄存在記憶體還是磁碟〉；桌面主機上的讀法見 [日誌判讀與診斷工具](/linux/dotfile/07-desktop-maintenance/log-reading-diagnostic-tools/)。服務失敗時主動通知、而不是事後翻 journal，見 [systemd OnFailure（失敗觸發鉤子）](/linux/dotfile/knowledge-cards/systemd-onfailure/)。

## 可觀察訊號

- `journalctl --list-boots` 只列出一次開機，而主機重開過機：紀錄只存在記憶體裡，重開機就清空。
- `journalctl --disk-usage` 印出 journal 目前佔用的空間。
- 某個服務的紀錄裡出現 `Suppressed N messages from <服務>`：那個服務在一段時間內寫得太多，超過速率限制的部分被丟掉了。
- `/var/log/journal` 目錄不存在：在 `Storage=auto` 的預設下，journal 只寫到 `/run/log/journal`。

## 設計責任

journald 的行為由 `/etc/systemd/journald.conf` 與 `/etc/systemd/journald.conf.d/*.conf` 決定，合併之後的值用 `systemd-analyze cat-config systemd/journald.conf` 讀；沒有寫出來的鍵取預設值，預設值要讀主機上那個版本的 `man journald.conf`，線上最新版的文件可能已經改了預設。下面的預設值取自 Oracle Linux 10 的 systemd 257 的 man page：

- **`Storage`**：紀錄存在哪裡。預設 `auto`：`/var/log/journal` 存在就寫磁碟，不存在就只寫記憶體。`persistent` 寫磁碟（需要時自己建目錄），`volatile` 只寫記憶體，`none` 全部丟掉。
- **`SystemMaxUse` 與 `SystemKeepFree`**：寫磁碟時的總量上限與要留給其他程式的空間，預設是檔案系統大小的 10% 與 15%，各自最多 4G。寫記憶體時改用 `RuntimeMaxUse` 與 `RuntimeKeepFree`，依 `/run` 的大小計算。到達上限時 journald 刪最舊的 journal 檔，所以 journal 本身不會把磁碟寫滿，代價是能回溯的時間長度隨寫入量浮動。
- **`RateLimitIntervalSec` 與 `RateLimitBurst`**：每個服務各自的速率限制，預設 30 秒內 10000 則，超過的部分丟掉並記一則丟了幾則的訊息；實際的門檻再乘上一個依剩餘磁碟空間算出的係數。一個服務出錯而大量輸出時，最有用的那幾行可能正好落在被丟掉的範圍裡。

常用的查詢：

```bash
journalctl -u nginx.service --since "2026-10-26 06:00"   # 單一服務、某個時間之後
journalctl -b -1 -p warning                              # 上一次開機、warning 以上的等級
journalctl --vacuum-size=500M                            # 立即把 journal 刪到 500M 以下（會刪資料）
```

`-u` 填 unit 名稱，`--since` 填要查的起點；`-b -1` 指上一次開機，紀錄只存在記憶體時沒有上一次開機可查；`--vacuum-size` 是會刪資料的指令，限制總量的長期做法是改 `SystemMaxUse`。

## 鄰卡

- [Ring Buffer（環狀緩衝區）](/linux/dotfile/knowledge-cards/ring-buffer-log/)
- [logrotate](/linux/dotfile/knowledge-cards/logrotate/)
- [systemd OnFailure（失敗觸發鉤子）](/linux/dotfile/knowledge-cards/systemd-onfailure/)
- [systemd drop-in（不改原檔的設定疊加）](/linux/dotfile/knowledge-cards/systemd-drop-in/)
