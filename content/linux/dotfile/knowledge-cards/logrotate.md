---
title: "logrotate"
date: 2026-10-26
description: "/var/log 底下的檔案越長越大、輪替之後新檔是空的而舊檔還在長、刪了 log 檔磁碟空間沒有回來，或要讀懂 /etc/logrotate.d/ 底下某個設定檔時"
weight: 55
tags: ["dotfile", "linux", "logging", "knowledge-cards"]
---

logrotate 是 Linux 上依排程輪替 log 檔的程式：到了設定的週期（每天、每週）或大小，它把目前的 log 檔改名成舊檔（`access.log` 變成 `access.log-20261026` 或 `access.log.1`）、建一個新的空檔讓程式接著寫、壓縮較舊的檔案，並刪掉超過保留份數的檔案。它管的是程式自己寫的文字 log 檔（nginx、rsyslog 轉出的 `/var/log/messages`）；[journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/) 的 journal 檔由 journald 自己依上限刪除，不經過 logrotate。

## 概念位置

logrotate 自己不常駐，由排程觸發：Oracle Linux 10 由 `logrotate.timer`（一個 [systemd timer](/linux/dotfile/knowledge-cards/systemd-timer/)）每天觸發一次；Debian 12 的套件同時裝了 `logrotate.timer` 與 [cron](/devops/infra/knowledge-cards/cron/) 的 `/etc/cron.daily/logrotate`，cron 的那一份在 systemd 執行中時直接結束，所以實際由 timer 觸發，沒有 systemd 的環境（例如容器）才改由 cron 觸發，前提是那個環境裡有 cron 在執行。這帶出它在磁碟用量裡的限制：輪替只發生在它被觸發的那一刻，兩次觸發之間 log 長多大它都不管，所以一份 log 在一天之內暴增（大量被拒絕的請求寫進 access log）時，logrotate 擋不住，這一類增長要靠磁碟用量的告警，見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/devops/operations/09-host-lifecycle/long-running-host-maintenance/)〈對外寫入端點的增長速度〉，以及 [Step Change（步階變化）](/backend/knowledge-cards/step-change/)。

## 可觀察訊號

- `/var/log/` 底下同一份 log 有一串帶日期或編號的舊檔，最舊的是 `.gz`：logrotate 有在跑。
- 只有一個越長越大的檔案、沒有舊檔：沒有對應的設定，或排程沒有啟用（`systemctl list-timers logrotate.timer` 查下一次觸發時間）。
- 輪替之後新的 `access.log` 一直是空的，而改名後的舊檔還在長：程式沒有重新開檔，見下面的 `postrotate`。
- 刪掉一個很大的 log 檔，`df` 的可用空間沒有增加：寫入的程式還開著那個檔案，`lsof +L1` 列得出已刪除而仍被開著的檔案。

## 設計責任

設定分兩層：`/etc/logrotate.conf` 是全域預設，`/etc/logrotate.d/` 底下每個套件放自己的一份，個別設定覆蓋全域預設。Oracle Linux 10 的 logrotate 3.22.0，全域預設是每週輪替、保留 4 份、檔名加日期；nginx 套件附的設定是：

```text
/var/log/nginx/*.log {
    create 0640 nginx root     # 改名之後建新檔，權限與擁有者
    daily                      # 每天輪替
    rotate 10                  # 保留 10 份舊檔，更舊的刪掉
    missingok                  # 檔案不存在不算錯誤
    notifempty                 # 空檔不輪替
    compress                   # 舊檔壓縮成 .gz
    delaycompress              # 最新的那一份舊檔先不壓縮
    sharedscripts              # 多個檔案只跑一次 postrotate
    postrotate
        /bin/kill -USR1 `cat /run/nginx.pid 2>/dev/null` 2>/dev/null || true
    endscript
}
```

- **`postrotate` 為什麼要送訊號**：程式開檔之後拿著的是檔案本身（inode），不是檔名。logrotate 把 `access.log` 改名之後，nginx 仍然寫進那個改了名的檔案，新建的 `access.log` 一直是空的。`USR1` 讓 nginx 關掉舊檔、依檔名重新開檔，之後才寫進新檔；`delaycompress` 讓還可能被寫入的那一份舊檔等到下一次才壓縮。
- **`copytruncate`**：給收不了訊號、不會重新開檔的程式用。logrotate 先複製一份、再把原檔截成零長度，程式繼續寫同一個檔案；代價是複製與截斷之間寫進來的幾行會遺失。
- **大小條件**（`size`、`maxsize`）：只在 logrotate 被觸發時檢查，觸發的間隔仍然是排程決定的。

logrotate 把每份 log 上一次輪替的時間記在狀態檔（Oracle Linux 是 `/var/lib/logrotate/logrotate.status`）。第一次看到一份 log 時，它只記下時間、不輪替，等週期到了才輪替；新加的設定要不要等一個週期才生效，看的是這個狀態檔。改完設定之後用 `logrotate -d /etc/logrotate.d/<設定檔>` 試跑：`-d` 只印出它會做什麼、不改任何檔案，輸出裡的 `log does not need rotating` 與 `rotating pattern` 那幾行寫出它對每份 log 的判斷。

## 鄰卡

- [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/)
- [systemd timer](/linux/dotfile/knowledge-cards/systemd-timer/)
- [Ring Buffer（環狀緩衝區）](/linux/dotfile/knowledge-cards/ring-buffer-log/)
