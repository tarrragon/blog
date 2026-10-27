---
title: "監控案例庫的來源與預期案例：JSONL 查詢效能、寫入 buffer、SDK 離線緩衝、跨平台時間戳、錯誤去重、遮罩誤判、聚合查詢掃描量"
date: 2026-10-27
description: "想知道監控案例庫收錄哪一類案例、案例從哪裡來，或想先看實作 SDK 與 Collector 時預期會遇到哪些狀況、各自在什麼條件下出現時讀"
tags: ["monitoring", "case-study"]
---

> **待更新**：這個案例庫的案例還沒有發佈。本篇先寫出案例的來源與預期會收錄的案例；每一個案例寫成文章之後，下面的表會換成連到那一篇的連結。

這篇說明監控案例庫收錄的案例從哪裡來、怎麼整理，以及預期會收錄的案例：JSONL 儲存的查詢效能、多個 SDK 同時送出時的寫入 buffer、SDK 在網路中斷時的離線 buffer、不同語言的時間戳精度差異、同一個 exception 重複回報時的去重、敏感資訊遮罩把正常內容誤判為 secret，以及長時間範圍聚合查詢的掃描量。每個預期案例都寫出它在什麼條件下出現，以及背後的機制寫在哪一個主題。

## 案例的來源：monitor repo 實作過程的紀錄

案例由 [tarrragon/monitor](https://github.com/tarrragon/monitor) 的實作過程產生，不是事前蒐集的。monitor 是一套開源、可以自架的客戶端監控工具，由 SDK 與 Collector 組成；實作時每一次遇到原本的設計無法處理的狀況，都在那個 repo 的 `docs/challenges/` 留下一筆紀錄，記下狀況出現的條件、排查過程與最後的處理。案例庫把這些紀錄整理成教學文章：保留出現的條件與機制，拿掉只屬於那個 repo 的細節。所以案例的數量與出現的順序取決於實作的進度，下表列的是依目前的設計預期會遇到的狀況。

## 預期收錄的案例與出現條件

| 預期案例                    | 出現的條件                                                | 背後的機制所在的主題                                   |
| --------------------------- | --------------------------------------------------------- | ------------------------------------------------------ |
| JSONL 儲存的查詢效能上限    | 事件累積超過約一萬筆，查詢要逐行讀過整個檔案              | [Collector 設計](/devops/monitoring/04-collector/)     |
| 高併發寫入的 buffer 策略    | 多個 SDK 同時 flush，Collector 同時收到大量寫入請求       | [Collector 設計](/devops/monitoring/04-collector/)     |
| SDK 離線 buffer 的事件遺失  | 網路中斷期間 buffer 寫滿，新事件沒有位置可放              | [SDK 設計模式](/devops/monitoring/03-sdk-design/)      |
| 跨平台的時間戳偏移          | JavaScript、Dart、Python 的 SDK 產生的時間戳精度不同      | [平台適配](/devops/monitoring/05-platform-adaptation/) |
| 錯誤去重的 fingerprint 設計 | 同一個 exception 在短時間內被重複回報                     | [SDK 設計模式](/devops/monitoring/03-sdk-design/)      |
| 敏感資訊遮罩的誤判          | 正常的欄位內容符合 secret 的比對樣式，被遮罩掉            | [資安與隱私](/devops/monitoring/07-security-privacy/)  |
| 聚合查詢的掃描量            | 查詢「過去 7 天的趨勢」這類長時間範圍的聚合，掃過全部事件 | [Collector 設計](/devops/monitoring/04-collector/)     |

表裡的門檻（「約一萬筆」）與條件是整理這張表時預期的值；案例寫成文章時，換成那一次實作實際遇到的值，以及那個值依什麼而變。
