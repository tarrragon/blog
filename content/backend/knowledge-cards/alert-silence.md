---
title: "Alert Silence（告警靜音）"
date: 2026-10-14
description: "維護期間要暫停某些告警的通知、或懷疑告警該響而沒響時，查 Alertmanager 的 silence 做什麼、它與抑制及週期性靜音時段的差別、它過期之前會藏住什麼，以及怎麼列出與監看還沒過期的靜音"
weight: 485
tags: ["backend", "observability", "alerting"]
---

Alert silence（告警靜音）是由人手動設定、在一段時間內不送出符合條件的告警通知的機制。Prometheus 生態裡由 Alertmanager 實作：一個 silence 由一組標籤條件（matchers）、開始與結束時間、設定者與註解組成，結束時間到了就自動失效。它和 [Alert Inhibition（告警抑制）](/backend/knowledge-cards/alert-inhibition/) 都是讓告警不送出通知，差別在觸發方式；長期不處理的靜音會讓 [Alert](/backend/knowledge-cards/alert/) 在故障時不送出。

## 概念位置

[抑制](/backend/knowledge-cards/alert-inhibition/)由另一則告警是否成立自動決定，原因的告警結束，被它壓下的症狀告警就恢復通知；靜音由人設定的時間範圍決定，與其他告警無關。Alertmanager 設定檔裡另有週期性的靜音時段（`time_intervals` 搭配路由的 `mute_time_intervals`，例如每週日凌晨的例行維護），那是寫在設定檔、每週重複的規則；silence 是一次性的，由人透過 API、網頁或 `amtool` 設下，必須有結束時間。所以 silence 用在一次性、已知會觸發告警的期間，例如擴充磁碟的維護、計畫中的資料庫切換。

靜音只壓通知：告警規則照常評估，Prometheus 的 `ALERTS` 時間序列照常記下這則告警成立；Alertmanager 的告警清單也查得到它，狀態是 `suppressed`，`silencedBy` 欄位指向壓下它的那個靜音。

## 可觀察訊號與例子

以 Alertmanager 0.28.1 實測建立、列出與結束一個靜音：

```bash
# --alertmanager.url 換成自己 Alertmanager 的網址；
# alertname 與 instance 換成要靜音的告警標籤，--author 填自己；
# --duration 填這次維護預計的時間，寧可短一點，維護沒結束時再延長
amtool --alertmanager.url=http://localhost:9093 silence add \
  alertname=DiskWillFillIn4Hours instance=db-1 \
  --duration=2h --author=oncall-a --comment="磁碟擴充維護"

# 列出還沒過期的靜音（含排定之後才開始的）：ID、條件、結束時間、設定者與註解
amtool --alertmanager.url=http://localhost:9093 silence query

# 提前結束一個靜音，<ID> 填 query 輸出第一欄的值
amtool --alertmanager.url=http://localhost:9093 silence expire <ID>
```

Alertmanager 自己輸出 `alertmanager_silences{state="active"}`、`{state="pending"}` 與 `{state="expired"}` 三個數字，分別是生效中、還沒開始與已過期的靜音數量。

## 判讀方式

靜音的風險在於結束時間比它對應的工作長：維護提早結束而靜音還在，這段時間同一條規則再成立，不會有任何通知，而從收件端看與一切正常沒有差別。降低風險的做法是設定時寫註解與合理的結束時間、接班時列出還沒過期的靜音逐一確認，以及讓 Prometheus 抓取 Alertmanager 的 `/metrics`，以 `alertmanager_silences{state="active"}` 寫一條「生效中的靜音數連續一天大於零」的 warning 規則。這個數字只是數量，分不出是同一個靜音一直生效還是幾個靜音輪流設下，所以它是提醒，逐一確認仍要讀每個靜音的開始與結束時間。這條規則的通知同樣經過 Alertmanager，條件寬鬆（例如只寫 `severity="warning"`）的靜音會連它一起壓下，所以設定靜音時條件至少寫到 `alertname`。規則的寫法與接班檢查的完整項目見 [4.29 值班的例行檢查](/backend/04-observability/on-call-routine-checks/)。
