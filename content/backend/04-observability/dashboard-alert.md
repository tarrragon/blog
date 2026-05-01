---
title: "4.4 dashboard 與 alert 設計"
date: 2026-04-23
description: "讓 dashboard 與 alert 對應 runbook 與容量趨勢"
weight: 4
---

## 大綱

- [dashboard](/backend/knowledge-cards/dashboard/) layout
- [alert](/backend/knowledge-cards/alert/) noise control
- [runbook](/backend/knowledge-cards/runbook/) linkage
- [on-call](/backend/knowledge-cards/on-call/) workflow

## 判讀訊號

- alert 跟 runbook 沒連、收到 page 不知道做什麼
- dashboard 數量爆量、無 owner、半年無人訪問
- 同一訊號多個 alert 重複觸發、無協調
- alert noise rate > 50%、ack 後無實際動作
- alert threshold 用直覺數字、沒對齊 SLO / 商業承諾

## 交接路由

- 04.6 SLI/SLO 訊號設計：alert 的訊號源頭
- 04.8 訊號治理閉環：alert / dashboard 的生命週期維運
- 04.10 client-side / RUM：補 server-side 看不到的 dashboard 維度
- 04.14 anomaly detection：rule-based alert 之外的統計訊號
