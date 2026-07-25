---
title: "Beacon"
date: 2026-07-06
description: "瀏覽器在頁面事件發生時主動送出、送出後不等回應的一則事件回報請求，用於靜態站把資料回傳給接收端"
weight: 1
tags: ["automation", "beacon", "sendbeacon", "knowledge-card"]
---

Beacon 是瀏覽器主動送出、且送出後不等待回應的一則事件回報請求。它的用途是把「頁面上發生了某件事」（被瀏覽、被點擊、即將關閉）這個事實，從使用者的瀏覽器回傳到一個接收端記錄下來。在靜態站的 [client beacon 架構](/automation/00-mental-model/static-site-and-glue-layer/)裡，beacon 是唯一能把瀏覽資料送回你手上的途徑——因為靜態站沒有伺服器 access log 可以被動記錄。可先對照 [web app 部署](/automation/knowledge-cards/web-app-deployment/)（beacon 送達的接收端怎麼來的）。

## 概念位置

Beacon 跟一般 API 請求的差別在「不等回應」。發起者送出後就繼續做自己的事，不阻塞、不讀回應、不重試——這種模式叫 fire-and-forget。對流量統計這類「送到就好、漏一兩筆無所謂」的場景，fire-and-forget 讓回報完全不影響使用者體驗。beacon 送出的請求由接收端的 [doPost](/automation/knowledge-cards/doget-dopost/) 進入點接住處理。

## 可觀察訊號與例子

瀏覽器的 `navigator.sendBeacon` 是專為此設計的 API：它保證即使頁面正在關閉，請求也會在背景送完，而且預設用 `text/plain` 送出，這一點在打跨網域端點時關鍵——`text/plain` 屬於 simple request、不觸發 CORS preflight。

## 判讀方式

跨網域打 Apps Script 這類端點時，`text/plain` 是否夠用決定要不要處理 CORS preflight。實作細節見[前端 beacon 與 CORS 障礙](/automation/02-analytics-beacon/frontend-beacon/)。
