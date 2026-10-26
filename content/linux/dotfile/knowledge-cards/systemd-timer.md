---
title: "systemd timer"
date: 2026-10-26
description: "排程的工作沒有在預期的時間執行、主機關機期間錯過的排程不知道會不會補跑、要在 cron 與 systemd timer 之間選一種寫定期工作，或讀到 *.timer 檔與 systemctl list-timers 的輸出時"
weight: 57
tags: ["dotfile", "linux", "systemd", "knowledge-cards"]
---

systemd timer 是 systemd 的排程機制：一個 `.timer` 檔寫出什麼時候觸發，到時間時 systemd 啟動同名的 `.service`（`logrotate.timer` 啟動 `logrotate.service`），由那個 service 執行實際的工作。跟 [cron](/infra/knowledge-cards/cron/) 一樣是定時執行指令，差別在被執行的工作是一個 systemd 服務：它的輸出進 [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/)、失敗時服務進入 failed 狀態，可以接 [systemd OnFailure（失敗觸發鉤子）](/linux/dotfile/knowledge-cards/systemd-onfailure/) 告警，資源限制與相依關係照 service 的寫法設定。

## 概念位置

timer 在一台長期上線的主機上負責那些不必有人登入、到時間就要做的事：[logrotate](/linux/dotfile/knowledge-cards/logrotate/) 輪替 log、`dnf-automatic` 下載與安裝安全更新、憑證的自動續約。這些工作有沒有在跑，要讀 timer 的狀態，不能只讀設定檔：設定檔寫好而 timer 沒有啟用時，工作一次都不會執行。各條更新管道交給 timer 的方式與檢查方法，見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)〈會老化的軟體：各條更新管道與更新後的重開機〉。

## 可觀察訊號

- `systemctl list-timers` 列出每個啟用中的 timer：`NEXT` 與 `LEFT` 是下一次觸發的時間與剩多久，`LAST` 與 `PASSED` 是上一次觸發，`UNIT` 是 timer、`ACTIVATES` 是它啟動的 service。一個 timer 不在這份列表裡，就是沒有啟用。
- `LAST` 是空的或很久以前：timer 從來沒觸發過，或觸發的條件從來沒成立。
- timer 有觸發而工作沒有完成：讀它啟動的 service，`systemctl status <名稱>.service` 與 `journalctl -u <名稱>.service`。

## 設計責任

Oracle Linux 10 的 `logrotate.timer` 是一個完整的例子：

```ini
[Unit]
Description=Daily rotation of log files

[Timer]
# 日曆時間：每天 00:00
OnCalendar=daily
# 在觸發時間之後隨機延遲 0 到 1 小時
RandomizedDelaySec=1h
# 主機關機期間錯過的那一次，開機後補跑
Persistent=true

[Install]
# systemctl enable 之後隨開機啟用
WantedBy=timers.target
```

註解寫在獨立的一行：unit 檔不支援寫在值後面的註解，`OnCalendar=daily # 每天` 的 `#` 之後會被當成值的一部分。

- **兩類觸發條件**：`OnCalendar=` 是日曆時間，`daily` 等於 `*-*-* 00:00:00`，寫法用 `systemd-analyze calendar "<表達式>"` 檢查，它印出正規化的寫法與下一次觸發時間；`OnBootSec=`、`OnUnitActiveSec=` 是相對時間（開機後多久、上一次執行後多久），適合「每隔一段時間跑一次」而不在乎幾點的工作。
- **`Persistent=true`**：只對 `OnCalendar=` 有效。systemd 把上一次觸發的時間記在磁碟上，開機時發現錯過了一次就立刻補跑；沒有這一行時，關機期間錯過的那一次就跳過。cron 沒有這個行為（`anacron` 補的是這一塊）。
- **`RandomizedDelaySec=`**：把很多台主機同一刻的工作打散，避免全部同時向同一個套件庫或 API 送請求；代價是執行時間不精確，要在固定時刻執行的工作不設它。
- **啟用的是 timer，不是 service**：`systemctl enable --now <名稱>.timer`。enable service 只處理 service 自己的 `[Install]` 段（`logrotate.service` 沒有這一段，enable 它會回報沒有安裝資訊），不會讓它定時執行。

跟 cron 的取捨：cron 一行寫完、在沒有 systemd 的環境（多數容器）也能用；timer 要寫兩個檔，換到的是補跑錯過的執行、輸出進 journal 可以查、失敗有狀態可以接告警。工作的失敗需要被看見時，timer 比較合適，因為 cron 的失敗只寄到本機的郵件，而郵件常常沒有設定。

## 鄰卡

- [cron](/infra/knowledge-cards/cron/)
- [systemd OnFailure（失敗觸發鉤子）](/linux/dotfile/knowledge-cards/systemd-onfailure/)
- [systemd drop-in（不改原檔的設定疊加）](/linux/dotfile/knowledge-cards/systemd-drop-in/)
- [logrotate](/linux/dotfile/knowledge-cards/logrotate/)
