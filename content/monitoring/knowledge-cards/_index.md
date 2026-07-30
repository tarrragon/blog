---
title: "Monitoring 知識卡片"
date: 2026-06-19
description: "監控體系相關的術語卡片索引"
tags: ["monitoring", "knowledge-cards"]
---

監控體系教學中出現的關鍵術語卡片。每張卡片說明一個語意責任，跨情境變義的概念拆成獨立卡片。

## 管線負載與資料保護

事件從 client 送出到 collector 收下的這段路上，容量與隱私是兩個獨立的約束：管線撐不撐得住決定哪些事件會被丟掉，而欄位能不能離開 client 決定哪些值根本不該送出。

| 卡片                                                                | 核心問題                               |
| ------------------------------------------------------------------- | -------------------------------------- |
| [Backpressure](/monitoring/knowledge-cards/backpressure/)           | 下游處理不完時如何讓上游慢下來         |
| [Rate Limiting](/monitoring/knowledge-cards/rate-limiting/)         | 單一 client 的量如何被限制在配額內     |
| [Sampling](/monitoring/knowledge-cards/sampling/)                   | 事件如何按比例丟棄以壓低管線負載       |
| [Redaction](/monitoring/knowledge-cards/redaction/)                 | 敏感欄位如何在離開 client 之前就被遮蔽 |
| [Error Fingerprint](/monitoring/knowledge-cards/error-fingerprint/) | 同一根因的錯誤如何被歸成一組           |

## 使用者行為分析

同一批事件可以回答三種不同的問題：誰跟誰該放在一起比、流程哪一步掉人、以及某個使用者現在值多少。三張卡各自對應一種分群或量化方式。

| 卡片                                                            | 核心問題                                 |
| --------------------------------------------------------------- | ---------------------------------------- |
| [Cohort Analysis](/monitoring/knowledge-cards/cohort-analysis/) | 有共同特徵的使用者如何被分群比較         |
| [Funnel Analysis](/monitoring/knowledge-cards/funnel-analysis/) | 多步驟流程每一步的轉換與流失如何被看見   |
| [RFM](/monitoring/knowledge-cards/rfm/)                         | 使用者價值如何用近期、頻率與金額三軸切分 |
