---
title: "Monitoring 知識卡片"
date: 2026-06-19
description: "監控體系相關的術語卡片索引"
tags: ["monitoring", "knowledge-cards"]
aliases: ["/monitoring/knowledge-cards/"]
---

監控體系教學中出現的關鍵術語卡片。每張卡片說明一個語意責任，跨情境變義的概念拆成獨立卡片。

## 管線負載與資料保護

事件從 client 送出到 collector 收下的這段路上，容量與隱私是兩個獨立的約束：管線撐不撐得住決定哪些事件會被丟掉，而欄位能不能離開 client 決定哪些值根本不該送出。

| 卡片                                                                       | 核心問題                               |
| -------------------------------------------------------------------------- | -------------------------------------- |
| [Backpressure](/devops/monitoring/knowledge-cards/backpressure/)           | 下游處理不完時如何讓上游慢下來         |
| [Rate Limiting](/devops/monitoring/knowledge-cards/rate-limiting/)         | 單一 client 的量如何被限制在配額內     |
| [Sampling](/devops/monitoring/knowledge-cards/sampling/)                   | 事件如何按比例丟棄以壓低管線負載       |
| [Redaction](/devops/monitoring/knowledge-cards/redaction/)                 | 敏感欄位如何在離開 client 之前就被遮蔽 |
| [Error Fingerprint](/devops/monitoring/knowledge-cards/error-fingerprint/) | 同一根因的錯誤如何被歸成一組           |

## 使用者行為分析

同一批事件可以回答三種不同的問題：誰跟誰該放在一起比、流程哪一步掉人、以及某個使用者現在值多少。三張卡各自對應一種分群或量化方式。

| 卡片                                                                   | 核心問題                                 |
| ---------------------------------------------------------------------- | ---------------------------------------- |
| [Cohort Analysis](/devops/monitoring/knowledge-cards/cohort-analysis/) | 有共同特徵的使用者如何被分群比較         |
| [Funnel Analysis](/devops/monitoring/knowledge-cards/funnel-analysis/) | 多步驟流程每一步的轉換與流失如何被看見   |
| [RFM](/devops/monitoring/knowledge-cards/rfm/)                         | 使用者價值如何用近期、頻率與金額三軸切分 |

## 追蹤碼在瀏覽器端的行為

商業追蹤碼裝進網站之後，在瀏覽器裡做的事有三件會影響資料的解讀：識別碼存在哪裡、存多久，哪些訪客的事件根本不會送出，以及網站沒有呼叫的事件從哪裡來。

| 卡片                                                                         | 核心問題                                         |
| ---------------------------------------------------------------------------- | ------------------------------------------------ |
| [First-party Cookie](/devops/monitoring/knowledge-cards/first-party-cookie/) | 追蹤碼的識別碼寫在誰的網域上、期限由誰決定       |
| [Headless Browser](/devops/monitoring/knowledge-cards/headless-browser/)     | 不開視窗的自動化瀏覽器會被追蹤碼怎麼對待         |
| [Autocapture](/devops/monitoring/knowledge-cards/autocapture/)               | 網站沒有呼叫的事件由誰產生、帶著哪些頁面上的內容 |

識別碼與瀏覽器指紋這兩種識別途徑的差別，見 automation 分類的 [Browser Fingerprint（瀏覽器指紋）](/automation/knowledge-cards/browser-fingerprint/)。
