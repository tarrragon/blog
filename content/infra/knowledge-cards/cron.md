---
title: "cron"
date: 2026-06-26
description: "Unix/Linux 的排程工作系統，按時間表自動執行指令。接手維運時要盤點所有 cron job"
weight: 32
tags: ["infra", "knowledge-cards"]
---

cron 是 Unix/Linux 系統內建的排程工作管理器，按預定的時間表自動執行指令。一個 cron job 定義「什麼時間跑什麼指令」，系統背景的 cron daemon 負責到時間就執行，管理 cron 通常透過 [SSH](/infra/knowledge-cards/ssh/) 存取伺服器。

## 概念位置

cron 在接手維運時是容易被忽略的隱藏工作——它不像 web 服務有明顯的入口，但可能負責資料庫備份、快取清除、報表產出、日誌清理等關鍵任務。漏掉一個 cron job 可能讓備份停止、快取永不過期、報表不再更新，而且不會立刻有人發現；常見的資料庫備份工具見 [mysqldump](/infra/knowledge-cards/mysqldump/)。

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

## 設計責任

cron job 要決定：排程頻率、執行失敗時的通知方式（cron 預設把輸出寄 email，但 email 常沒配好）、日誌記錄（指令的 stdout/stderr 導到 log 檔）。遷移或升級時，cron job 要隨著遷移——忘了搬等於停掉排程但沒人知道。

雲端替代品：AWS CloudWatch Events / EventBridge、GCP Cloud Scheduler、Azure Logic Apps。這些服務提供 web UI 管理、失敗通知、執行歷史，但需要額外設定。

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — 盤點和管理 cron 需要 SSH 存取
