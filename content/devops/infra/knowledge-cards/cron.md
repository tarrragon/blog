---
title: "cron"
date: 2026-06-26
description: "Unix/Linux 的排程工作系統，按時間表自動執行指令。接手維運時要盤點所有 cron job"
weight: 32
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/cron/"]
---

cron 是 Unix/Linux 系統內建的排程工作管理器，按預定的時間表自動執行指令。一個 cron job 定義「什麼時間跑什麼指令」，系統背景的 cron daemon 負責到時間就執行，管理 cron 通常透過 [SSH](/devops/infra/knowledge-cards/ssh/) 存取伺服器。

## 跟其他概念的關係

cron 在接手維運時是容易被忽略的隱藏工作——它不像 web 服務有明顯的入口，但可能負責資料庫備份、快取清除、報表產出、日誌清理等關鍵任務。漏掉一個 cron job 可能讓備份停止、快取永不過期、報表不再更新，而且不會立刻有人發現；常見的資料庫備份工具見 [mysqldump](/devops/infra/knowledge-cards/mysqldump/)。

## crontab 格式

```text
# 分 時 日 月 週  指令
0  3  *  *  *    /usr/bin/php /var/www/backup.php
*/5 * *  *  *    /usr/bin/curl -s https://example.com/cron/heartbeat
0  0  1  *  *    /usr/bin/find /tmp -mtime +7 -delete
```

五個時間欄位依序是分鐘（0-59）、小時（0-23）、日（1-31）、月（1-12）、星期幾（0-7，0 和 7 都是星期日）。`*` 代表「每一個」，`*/5` 代表「每 5 個」。

## 可觀察訊號

接手維運時盤點 cron job：

```bash
# 當前使用者的 crontab
crontab -l

# 所有使用者的 crontab（需要 root）
for user in $(cut -f1 -d: /etc/passwd); do
  crontab -u "$user" -l 2>/dev/null && echo "=== $user ==="
done

# 系統級 cron
cat /etc/crontab
ls /etc/cron.d/
```

沒有 SSH 時（cPanel 環境），在 cPanel 的「Cron 工作」頁面查看和匯出。

## 判斷條件與後果

cron job 跑失敗時不會有使用者看到錯誤畫面，所以除了排程頻率，另外兩項設定決定失敗是否被人看見。失敗通知：cron 預設把輸出寄 email，主機的 email 沒配好時這封信寄不出去，失敗沒有人收到。日誌記錄：指令的 stdout/stderr 沒有導到 log 檔時，事後查不到它哪一次失敗、為什麼失敗。遷移或升級主機時，cron job 不會跟著程式碼一起搬，新主機上漏設的排程就此停止，同樣沒有錯誤畫面，備份停了或報表不再更新要等到有人需要那份資料時才發現。

用 systemd 的主機上，同一類定期工作也可以寫成 [systemd timer](/linux/dotfile/knowledge-cards/systemd-timer/)：多寫一個檔，換到的是關機期間錯過的執行開機後補跑、輸出進 journal、失敗有狀態可以接告警。

雲端替代品：AWS CloudWatch Events / EventBridge、GCP Cloud Scheduler、Azure Logic Apps。這些服務提供 web UI 管理、失敗通知、執行歷史，但需要額外設定。

## 鄰卡

- [SSH](/devops/infra/knowledge-cards/ssh/) — 盤點和管理 cron 需要 SSH 存取
