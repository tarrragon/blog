---
title: "systemd watchdog 與自動重啟"
date: 2026-07-03
description: "在單機 systemd 上做服務自動恢復時，釐清 watchdog 主動報活與 restart policy 被動拉起是兩套機制、以及為什麼要先重啟幾次才放棄"
weight: 3
tags: ["devops", "systemd", "watchdog", "auto-restart", "liveness"]
---

單機 systemd 上的自動恢復由兩套獨立機制組成：watchdog 讓服務定期主動報活、超時沒報就被 systemd 重建；restart policy 在進程退出後把它重新拉起。前者對應 [liveness 探針](/devops/04-service-health/liveness-vs-readiness/) 的語意——服務宣告自己還在運作；後者對應進程層的崩潰恢復。兩者觸發條件不同、覆蓋的失效模式也不同，一個服務常常兩套都要。

在編排平台上，這兩件事由 probe 機制表達；在單機部署，systemd 靠 `sd_notify` 協議讓服務明確宣告狀態，反而比 probe 更直接——服務主動說「我還活著」「我準備好了」，不必外部反覆猜測。

## Watchdog：服務主動報活，超時就被重建

Watchdog 是主動式的 liveness：服務端定期呼叫 `sd_notify(WATCHDOG=1)` 告訴 systemd 「我還在正常運作」，systemd 設定一個 `WatchdogSec=` 逾時；服務在時限內沒報，systemd 判定它卡死、自動 kill 加 restart。本站 collector 用的是 `WatchdogSec=30s`——服務要在 30 秒內報一次，逾時就被重啟。

Watchdog 抓的正是 [進程活著但子系統死掉](/linux/debug/process-service-state-diagnosis/) 那類失效：進程還在、`systemctl is-active` 還顯示 active，但內部某個關鍵迴圈已經 hung。這種狀態下崩潰恢復幫不上忙（進程根本沒退出），但 watchdog 抓得到——因為卡死的服務報不出那一次心跳。前提是服務改得動：`sd_notify(WATCHDOG=1)` 要寫進服務自己的碼，報活的位置要放在「真的有在做事才會經過」的路徑上，才不會變成一個進程活著就自動報活的假訊號。

服務改不動的情況（閉源程式、別人的服務），watchdog 這條用不上，改從外部主動戳它——一個定時器對服務發健康請求並設逾時，戳不動就讓那次檢查失敗。這個外部探針的完整單機實作在 [服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/) 的外部健康探針段。Watchdog 跟外部探針的分界就是「控不控制得了那個服務」：控制得了用 watchdog（零額外依賴、服務自己報），控制不了用外部探針（從體外戳）。

## Restart policy：進程退出後被拉起

Restart policy 覆蓋的是進程真的退出的情況——崩潰、被 kill、非正常結束。`Restart=on-failure` 讓 systemd 在服務以失敗狀態退出時自動重啟，`RestartSec=5` 設定重啟前等幾秒。這是最基本的崩潰恢復：多數暫時性失敗（一次連線抖動、一個 race）重試一下就好，不值得驚動人。

但無限重啟會掩蓋真正壞掉的服務——一個因為配置錯誤永遠起不來的服務，會被 restart policy 反覆拉起、反覆失敗。所以要配重試上限：`StartLimitBurst=3` 加 `StartLimitIntervalSec=60` 表示 60 秒內失敗 3 次才真的進 failed 狀態、停止重試。本站 collector 用的門檻是 10 分鐘內重啟 3 次以上就停止自動重啟、改發告警要求人工介入——這條門檻是「機器自動恢復」跟「人工恢復」的交界：撞上限之前交給機器重試，撞上限之後承認自動恢復無效、升級成人的問題。

## 先自動重啟，放棄了才告警

自動恢復跟告警是兩段，要分開。理由是多數失敗自己重試就會過，每次瞬斷都吵人會把告警洗到沒人看。正確的分段是：restart policy 負責「重試幾次」，告警只在「重試上限撞到、真的放棄」時才發。

這裡有個實測踩到、跟直覺相反的意外：systemd 的 [`OnFailure`](/linux/dotfile/knowledge-cards/systemd-onfailure/) 鉤子不是「放棄才觸發」，而是每一次失敗都觸發——包含 `Restart=on-failure` 的每次 auto-restart 中途。[服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/) 實測一個反覆崩潰、重試 3 次後放棄的服務，`OnFailure` 觸發了 4 次（3 次 auto-restart 加 1 次最終放棄）。這個觸發次數是特定 systemd 版本的實測，`OnFailure` 與 `Restart=` 的互動跨版本調整過，換一個版本可能量到不同次數，但「每次失敗都觸發、不是只在放棄時」這個機制本身跨版本成立。所以只靠 restart 加 start-limit 的 config，每次瞬斷都會發告警。真正做到「只在放棄才吵」，要在告警處理器裡加一道狀態閘門——auto-restart 中途服務的 `ActiveState` 是 `activating`、撞上限進 failed 才是 `failed`，處理器只在 `failed` 才送，加上這道閘門後同一個崩潰測試從 4 則告警降到 1 則。config 管重試次數、handler 的閘門管只在終局告警，兩段合起來才是完整的「先重啟、放棄才吵」。這道告警鏈的完整設定（`OnFailure` 鉤子、送出腳本、遞迴陷阱）在那篇有實測驗證過的完整版，本模組不重述。

## 恢復閉環要回饋到狀態呈現

自動恢復做完之後，狀態呈現要跟著收斂。collector 在自動恢復成功後送一個 `collector.started` 事件，讓 DevOps 儀表板的服務狀態卡從紅轉綠；撞到重啟上限、升級成人工告警時，狀態卡維持紅色等人處理。恢復機制跟呈現層的這個回饋迴路，讓「服務掉了又自己回來」這件事在看板上留下可追溯的痕跡，而不是靜默地掉了又靜默地回來。收斂成儀表板的細節見 [Monitoring DevOps 儀表板](/monitoring/04-collector/dashboard-devops/)。

## 下一步路由

- Watchdog 對應的概念層 liveness、restart 對應的重啟代價 → [Liveness 與 Readiness](/devops/04-service-health/liveness-vs-readiness/)
- 單機 systemd 之外，supervisord、Docker、Kubernetes 怎麼表達重啟與重建 → [Process supervisor 選型](/devops/04-service-health/process-supervisor-selection/)
- 告警鏈的完整單機實作（OnFailure、送出腳本、心跳、canary）→ [服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)
- 重啟前先讓服務有序收束在途工作 → [Graceful shutdown](/devops/04-service-health/graceful-shutdown/)
