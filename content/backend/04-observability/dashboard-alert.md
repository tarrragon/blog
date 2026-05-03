---
title: "4.4 dashboard 與 alert 設計"
date: 2026-04-23
description: "讓 dashboard 與 alert 對應 runbook 與容量趨勢"
weight: 4
---

## 大綱

- [dashboard](/backend/knowledge-cards/dashboard/) layout
- [alert](/backend/knowledge-cards/alert/) noise control / [alert fatigue](/backend/knowledge-cards/alert-fatigue/)
- [runbook](/backend/knowledge-cards/runbook/) linkage
- [on-call](/backend/knowledge-cards/on-call/) workflow

## 概念定位

[dashboard](/backend/knowledge-cards/dashboard/) 與 [alert](/backend/knowledge-cards/alert/) 是把觀測訊號轉成操作入口的控制面，責任是讓團隊在正常巡檢與事故響應時看到同一組事實。

這一頁處理的是視覺化與通知節奏。dashboard 讓人理解狀態，alert 讓人採取行動；兩者都需要 [ownership](/backend/knowledge-cards/ownership/)、生命週期與 [runbook](/backend/knowledge-cards/runbook/) 連結。

## 核心判讀

判讀 dashboard / alert 時，先看訊號是否對應決策，再看通知是否會觸發實際動作。

重點訊號包括：

- alert 是否能對應到明確 [runbook](/backend/knowledge-cards/runbook/)、[ownership](/backend/knowledge-cards/ownership/) 與停止條件
- dashboard 是否有固定使用者與更新責任
- threshold 是否對齊 SLO、容量邊界或使用者影響
- noise rate 是否被追蹤並回寫治理流程

## 判讀訊號

- alert 跟 [runbook](/backend/knowledge-cards/runbook/) 沒連、收到 page 不知道做什麼
- dashboard 數量爆量、無 owner、半年無人訪問
- 同一訊號多個 alert 重複觸發、無協調
- alert noise rate > 50%、ack 後無實際動作，形成 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)
- alert threshold 用直覺數字、沒對齊 SLO / 商業承諾

## 交接路由

- 04.6 SLI/SLO 訊號設計：alert 的訊號源頭
- 04.8 訊號治理閉環：alert / dashboard 的生命週期維運
- 04.10 client-side / RUM：補 server-side 看不到的 dashboard 維度
- 04.14 anomaly detection：rule-based alert 之外的統計訊號
