---
title: "6.8 高併發下的 Redis 與 SQL 使用原則"
date: 2026-04-23
description: "從 Go 服務角度整理 Redis 與 SQL 的高併發存取邊界"
weight: 8
---

這一章從 Go 服務的角度整理資料存取原則。重點在於：當併發增加時，Go 端要用明確邊界使用 Redis 或 SQL，讓下游維持可承受的請求節奏。

## 本章目標

學完本章後，你將能夠：

1. 理解高併發下最常見的資料存取風險
2. 區分 Redis 與 SQL 各自適合的角色
3. 用 connection pool、timeout 與批次策略控制壓力
4. 避免 cache stampede 與慢查詢連鎖
5. 在 Go 服務內設計可控的下游存取邊界

---

## 【觀察】Go 端要先控住請求節奏

高併發時，資料存取風險通常來自請求節奏超過下游承受能力。你可以有很多 goroutine，但 Redis 與 SQL 不會因為 goroutine 多就自動變快。

Go 端通常要先做的是：

- 限制同時對下游發出的請求數
- 設定明確 timeout
- 避免無限 fan-out
- 在壓力過高時拒絕新工作

## 【判讀】Redis 適合快取、狀態與短生命週期資料

Redis 在 Go 服務裡常見用途包括：

- cache
- session
- counter
- rate limit
- idempotency key
- queue / stream

Go 端使用 Redis 時要注意：

| 問題            | 風險                        |
| --------------- | --------------------------- |
| 熱 key          | 單點壓力過大                |
| cache miss 擁塞 | 大量 goroutine 同時打到後端 |
| pipeline 太大   | buffer 與記憶體壓力增加     |
| 缺少 timeout    | 慢 request 會堆積成連鎖問題 |

## 【判讀】SQL 適合正式狀態與一致性資料

SQL 在 Go 服務裡通常承接的是：

- 最終狀態
- 查詢
- 交易
- 可追蹤資料

Go 端最重要的原則是共用 `*sql.DB`，讓 connection pool 真正發揮作用，並讓每個 query 都有 context 與 timeout。

需要特別注意的是：

- 太高的同時連線數會壓垮資料庫
- 太長的 transaction 會卡住連線池
- 慢查詢會把 goroutine 一起拖住

## 【策略】Go 端要用邊界保護下游

高併發下的資料存取，通常要搭配以下做法：

- `sql.DB` 與 Redis client 長期共用
- 所有操作都帶 `context`
- 用 worker pool 或 semaphore 控制同時請求數
- 對 cache miss 做去重或保護
- 對寫入高峰做批次或排隊

這些做法是讓高併發系統能長時間穩定運行的基本條件。

## 小結

Go 服務在 Redis 與 SQL 上的關鍵是用請求節奏、timeout、pool 與 backpressure 保護下游。下游邊界清楚時，Go 的高併發能力才會真正變成優勢。
