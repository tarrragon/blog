---
title: "Dead Man's Switch（心跳監看）"
date: 2026-10-14
description: "需要知道監控或排程工作自己停掉了、而它停掉時發不出任何告警時，以「期限內沒收到訊號就通知」反過來判斷"
weight: 475
tags: ["backend", "observability", "reliability"]
---

Dead man's switch（心跳監看）是一種反過來的告警：被監看的系統持續送出「我還在」的訊號（心跳），監看者在約定的期限內沒收到就發出通知。一般的告警要被監看的系統自己發出，系統停掉時就發不出來；心跳監看把判斷交給另一方，系統停掉正好是心跳中斷，所以這個情形也通知得到。監看者必須落在被監看系統的 [Failure Domain](/backend/knowledge-cards/failure-domain/) 以外，它送出的是一種 [Out-of-Band Signal](/backend/knowledge-cards/out-of-band-signal/)。

## 概念位置

心跳監看是 [Alert](/backend/knowledge-cards/alert/) 的反向形式：一般告警在條件成立時送出，心跳監看在訊號消失時送出。它回答的問題是「被監看的系統還在不在運作」，不回答使用者能不能用服務：監控照常送心跳時，使用者仍可能因為 DNS 或入口故障連不進來，那一種由從外面發請求的外部探測回答。兩者互補，見 [4.28 單台主機的監控盲區與外部視角](/backend/04-observability/single-host-monitoring-outside-view/)。

用在 Prometheus 上時，心跳是一條永遠成立的告警規則（kube-prometheus-stack 叫它 `Watchdog`），Alertmanager 每隔固定時間把它送到監看者的網址；規則評估、Alertmanager 的路由與送出這三段任何一段停掉，心跳都會中斷。排程工作（備份、資料匯出）也用同一個做法：工作完成時送一次心跳，沒按時送到就代表工作沒跑或跑失敗。

## 可觀察訊號與例子

監看者以「期限」與「寬限」判斷：期限是預期的心跳間隔，寬限是容許的延遲，最後一次收到心跳之後超過兩者相加還沒有新的，就判定中斷。實測開源的 healthchecks 設期限與寬限各 1 分鐘，停掉 Alertmanager 之後，通知在最後一次心跳之後 2 分鐘寄出，判斷的起點是最後一次收到心跳的時間，不是系統停掉的時間。多數心跳監看服務另外提供回報失敗的網址（healthchecks 是 ping 網址加上 `/fail`），收到就立刻判定失敗，不必等期限。

## 判讀方式

心跳的送出間隔要小於期限加寬限，而且要算進送出端的時間粒度：Alertmanager 只在 `group_interval` 的時間點檢查要不要重送，實際的間隔是 `repeat_interval` 加上最多一個 `group_interval`（設定見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)）。監看者本身的通知管道也不能經過被監看的系統，否則心跳中斷的通知會走那條已經停掉的路。最後，心跳監看平時不會觸發，要刻意停掉被監看的系統演練一次，確認通知真的會到。
