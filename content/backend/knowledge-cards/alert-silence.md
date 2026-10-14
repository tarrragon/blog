---
title: "Alert Silence（告警靜音）"
date: 2026-10-14
description: "維護期間要暫停某些告警的通知、或懷疑告警該響而沒響時，查 Alertmanager 的 silence 做什麼、它與抑制的差別、它過期之前會藏住什麼，以及怎麼列出與監看生效中的靜音"
weight: 485
tags: ["backend", "observability", "alerting"]
---

Alert silence（告警靜音）是由人手動設定、在一段時間內不送出符合條件的告警通知的機制。Prometheus 生態裡由 Alertmanager 實作：一個 silence 由一組標籤條件（matchers）、開始與結束時間、設定者與註解組成，結束時間到了就自動失效。它和 [Alert Inhibition（告警抑制）](/backend/knowledge-cards/alert-inhibition/) 都是讓告警不送出通知，差別在觸發方式；長期不處理的靜音會讓 [Alert](/backend/knowledge-cards/alert/) 在故障時不響。

## 概念位置

[抑制](/backend/knowledge-cards/alert-inhibition/)由另一則告警是否成立自動決定，原因的告警結束，被它壓下的症狀告警就恢復通知；靜音由人設定的時間範圍決定，與其他告警無關。所以靜音用在已知會觸發告警的期間，例如擴充磁碟的維護、計畫中的資料庫切換。靜音只壓通知：告警規則照常評估，被靜音的告警仍然在 Alertmanager 與 Prometheus 裡留下成立的紀錄。

## 可觀察訊號與例子

以 Alertmanager 0.28 實測，`amtool silence add alertname=DiskWillFillIn4Hours instance=db-1 --duration=2h --author=oncall-a --comment="磁碟擴充維護"` 建立一個兩小時的靜音，`amtool silence query` 列出每一個生效中靜音的 ID、條件、結束時間、設定者與註解，`amtool silence expire <ID>` 提前結束它。Alertmanager 自己輸出 `alertmanager_silences{state="active"}`、`{state="pending"}` 與 `{state="expired"}` 三個數字，分別是生效中、還沒開始與已過期的靜音數量。

## 判讀方式

靜音的風險在於結束時間比它對應的工作長：維護提早結束而靜音還在，這段時間同一條規則再成立，值班收不到通知，而從收件端看與一切正常沒有差別。降低風險的做法是設定時寫註解與合理的結束時間、開班時列出生效中的靜音逐一確認，以及以 `alertmanager_silences{state="active"}` 寫一條「有靜音持續生效超過一天」的 warning 規則。開班檢查的完整項目見 [4.29 值班的例行檢查](/backend/04-observability/on-call-routine-checks/)。
