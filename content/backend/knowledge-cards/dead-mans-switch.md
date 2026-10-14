---
title: "Dead Man's Switch（心跳監看）"
date: 2026-10-14
description: "需要知道監控或排程工作自己停掉了、而它停掉時發不出任何告警時，以「時限內沒收到訊號就通知」反過來判斷"
weight: 475
tags: ["backend", "observability", "reliability"]
---

Dead man's switch（心跳監看）是一種反過來的告警：被監看的系統持續送出「我還在」的訊號（心跳），監看者在約定的時限內沒收到就發出通知。一般的告警要被監看的系統自己發出，系統停掉時就發不出來；心跳監看把判斷交給另一方，系統停掉正好是心跳中斷，所以這個情形也通知得到。監看者必須落在被監看系統的 [Failure Domain](/backend/knowledge-cards/failure-domain/) 以外，它送出的是一種 [Out-of-Band Signal](/backend/knowledge-cards/out-of-band-signal/)（失效域以外送出的訊號）。

## 概念位置

心跳監看是 [Alert](/backend/knowledge-cards/alert/) 的反向形式：一般告警在條件成立時送出，心跳監看在訊號消失時送出。它回答的問題是「被監看的系統還在不在運作」，不回答使用者能不能用服務：監控照常送心跳時，使用者仍可能因為 DNS 或入口故障連不進來，那一種由從外面發請求的外部探測回答。兩者互補，見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。

用在 Prometheus 上時，心跳是一條永遠成立的告警規則（kube-prometheus-stack 叫它 `Watchdog`），Alertmanager 每隔固定時間把它送到監看者的網址；規則評估、Alertmanager 的路由與送出心跳的那個 receiver 任何一段停掉，心跳都會中斷；它只走送心跳的那一個 receiver，人實際收告警的其他通知管道壞掉時，心跳照常送達（規則評估停掉時晚一段才中斷，因為 Alertmanager 在已收到的告警結束時間之前照常重送）。排程工作（備份、資料匯出）也用同一個做法：工作完成時送一次心跳，沒按時送到就代表工作沒跑、跑失敗，或送心跳的那條路斷了。systemd 的 `WatchdogSec` 也叫 watchdog，它在同一台主機上由 systemd 監看程序、程序沒回報就重啟，觀察者與被監看者在同一個失效域，與這裡的心跳監看是兩件事。一次以 Watchdog 告警搭配外部偵測器的案例見 [Watchdog / dead man's switch](/backend/04-observability/cases/watchdog-dead-mans-switch/)。

## 可觀察訊號與例子

監看者以週期（period，預期的心跳間隔）與寬限（grace time，容許的延遲）判斷：最後一次收到心跳之後超過週期加寬限還沒有新的，就判定中斷。以開源的 healthchecks 實測，週期與寬限各設 1 分鐘，停掉送心跳的 Alertmanager 之後，通知在最後一次心跳之後 2 分鐘寄出：判斷的起點是最後一次收到心跳的時間，不是系統停掉的時間（實測的時間線見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/) 的〈心跳中斷的演練〉）。healthchecks 這類服務另外提供回報失敗的網址：服務替每個檢查項目發一個接收心跳的網址（ping 網址），加上 `/fail` 就是回報失敗，收到就立刻判定失敗，不必等週期。

## 判讀方式

心跳的送出間隔要小於週期加寬限，而且要算進送出端的時間粒度：Alertmanager 只在 `group_interval` 的時間點檢查要不要重送，實際的間隔最長是 `repeat_interval` 加一個 `group_interval`（設定見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 的〈Watchdog：告警鏈本身的心跳〉）。監看者本身的通知管道也不能經過被監看的系統，否則心跳中斷的通知會走那條已經停掉的路。監看者的中斷通知平時不會發出，它會不會發出、送不送得到人手上，只有刻意停掉被監看的系統才看得到，演練的範圍、安全邊界與成功標準怎麼定見 [Game Day](/backend/knowledge-cards/game-day/)，演練的時間線見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/) 的〈心跳中斷的演練〉。
