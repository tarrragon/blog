---
title: "模組一：進階並發模式"
date: 2026-04-22
description: "channel ownership、select loop、非阻塞送出、共享狀態、worker pool 與 rate limiting"
weight: 1
---

Go 並發設計的核心是明確定義 ownership、生命週期、背壓與共享狀態邊界。goroutine 很便宜，但失控的 goroutine、關閉錯誤的 channel、無限制堆積的 buffer，以及外洩的可變資料都會讓服務難以維護。

本模組承接入門篇的 goroutine、channel、select、mutex 基礎，進一步處理長時間運行服務會遇到的問題：誰能關閉 channel、worker 如何停止、channel 滿載時怎麼回應、共享 map/slice 如何避免 data race、工作量如何限制、入口速率如何控制。

## 章節列表

| 章節                      | 主題                         | 關鍵收穫                                        |
| ------------------------- | ---------------------------- | ----------------------------------------------- |
| [1.1](channel-ownership/) | channel ownership 與關閉責任 | 用 sender lifecycle 判斷誰能 close channel      |
| [1.2](select-loop/)       | select loop 的生命週期設計   | 同時處理輸入、ticker、取消與資源釋放            |
| [1.3](non-blocking-send/) | 非阻塞送出與事件丟棄策略     | 把 channel 滿載轉成明確服務行為                 |
| [1.4](shared-state/)      | 共享狀態與複製邊界           | 用 lock、copy 與 owner method 保護可變資料      |
| [1.5](worker-pool/)       | bounded worker pool          | 限制同時執行的工作量，避免 goroutine 無限制堆積 |
| [1.6](rate-limit/)        | rate limiting 與背壓         | 用本地速率限制保護服務入口與下游依賴            |

## 本模組使用的範例主題

本模組使用虛構的通知與工作處理服務作為範例。範例會包含背景 worker、事件佇列、即時推送、狀態 repository 與測試 fake。

範例只用來展示 Go 並發設計方法，不假設讀者正在維護任何特定專案。

## 本模組的 Go 核心概念

- 用 channel direction 表達 send-only 與 receive-only 能力。
- 用 context 作為 goroutine 停止訊號。
- 用 select 管理多種輸入與 ticker。
- 用 buffered channel 吸收短暫尖峰，但不把 buffer 當成容量規劃替代品。
- 用 mutex 保護共享 map/slice。
- 用 copy boundary 防止呼叫端修改內部狀態。
- 用 worker pool 控制同時執行數。
- 用 rate limiter 把過量輸入轉成可預期回應。
- 用 race detector 與 focused tests 驗證並發邊界。

## 學習重點

學完本模組後，你應該能判斷：

1. 哪個 goroutine 擁有 channel 的關閉責任
2. 一個長期 worker 停止時需要釋放哪些資源
3. channel 滿載時應該等待、回錯、丟棄還是降級
4. map、slice、pointer 何時會洩漏內部狀態
5. 什麼情況下 mutex 比 channel 更適合表達狀態擁有權
6. 什麼情況下需要 bounded worker pool
7. 入口過量時應排隊、限速、拒絕還是降級

## 本模組不處理

本模組不討論分散式鎖、actor framework 或高階 queue 系統。這些主題建立在本模組的基礎之上；本模組先把單一 Go process 內的 goroutine、worker、速率與共享資料邊界講清楚。外部 broker 與分散式流量治理會放在 [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/) 與 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。

## 先備知識

- [Go 入門：並發模型](../../go/04-concurrency/)
- 知道 goroutine、channel、select、mutex 的基本用法

## 學習時間

預計 4-5 小時
