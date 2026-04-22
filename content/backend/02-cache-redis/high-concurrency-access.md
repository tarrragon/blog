---
title: "2.1 高併發下的 Redis 讀寫邊界"
date: 2026-04-22
description: "說明 Go 服務在高併發下如何共用 Redis client、控制 pipeline 與避免 cache stampede"
weight: 1
---

Redis 在 Go 服務裡最常扮演的是 cache、session、counter、dedup、presence 或輕量協調層。它通常比 SQL 更適合高併發短操作，但前提是你把 client、連線池、pipeline 與 key 設計控制好。高併發下的 Redis 不會因為是 NoSQL 就自動簡單，熱點 key、快取穿透、stampede、過大 pipeline 與不當鎖設計一樣會出問題。

## 本章目標

學完本章後，你將能夠：

1. 理解為什麼 Redis client 應該共用
2. 分辨單鍵操作、pipeline、transaction 與 Lua 的邊界
3. 了解高併發下的 cache stampede 與 hot key 問題
4. 用 `context` 與 timeout 保護 Redis 呼叫
5. 把 Redis 用在適合的資料角色，而不是把它當成萬用資料庫

---

## 【觀察】Redis 呼叫大多是網路 I/O

Go 端對 Redis 的操作，通常是短小但頻繁的網路請求。這代表真正影響效能的往往不是 CPU，而是 RTT、連線重用、批次送出與 key 設計。

所以高併發時，最重要的不是「要不要再開更多 goroutine」，而是：

- 用同一個 client 共用連線池
- 對獨立操作使用合理的 pipeline
- 不要讓單一 key 成為所有流量的集中點

## 【判讀】client 共用比每次建立更重要

Redis client 的核心設計通常就是讓應用共用同一個實例。每個 request 都 new client，會把連線管理成本、握手成本與資源回收問題全部放大。

高併發服務通常會採用：

- process 啟動時建立一個 Redis client
- request handler、worker、service layer 共用它
- 所有操作都帶 `context`
- timeout 與取消由上層傳入

## 【策略】pipeline 用來省 RTT，不是無限加速器

pipeline 的價值是把多個獨立命令一次送出，減少往返次數。它很適合：

- 多個彼此獨立的讀取
- 批次寫入
- 一次更新多個 cache key

但 pipeline 不是把命令全塞進去就好。太大的 pipeline 會帶來：

- 內存壓力
- 回應延遲變大
- 單次失敗影響更多操作

## 【判讀】原子性需求要分清楚

Redis 的很多操作本身就可以很快，但不是所有需求都能靠「快」解決。當你需要的是原子性或一致性，才應該考慮：

- 單鍵原子操作
- transaction
- Lua script
- 由上層做去重或補償

不要把 transaction 當成預設選項，也不要把 cache 寫入誤當成業務真相。Redis 很常是輔助狀態，真正的 source of truth 通常還是在 SQL 或 domain store。

## 【策略】cache stampede 與 hot key 要先處理

高併發快取最常見的兩個問題，是大量 goroutine 同時 miss 同一筆資料，以及大量流量打到同一個 key。

### cache stampede

當 cache miss 發生時，如果每個 request 都直接回源查 DB，會把後端放大成更大的壓力。常見的處理方式包括：

- 設定合理 TTL
- 加 single-flight 類型的去重
- 讓部分請求等待同一批重建結果
- 對重建失敗設退避或短暫保護

### hot key

如果某些 key 過度熱門，壓力會集中到 Redis 甚至單一 shard。處理方式通常是：

- 拆 key 或拆資料粒度
- 讓讀取走多層 cache
- 降低單點依賴
- 在應用端做短暫本地快取或節流

## 【執行】把 Redis 用在對的角色

Redis 在高併發場景常見角色有：

- cache
- session store
- counter / rate limit
- presence / online state
- dedup / idempotency key
- lightweight queue / stream

每一種角色的容錯方式不同。像 counter、presence 和 cache 的失敗語意就不一樣，不能都用同一種寫法處理。

## 【策略】分散式 lock 要謹慎使用

Redis 常被拿來做 distributed lock，但這類機制要非常清楚 lease、過期、持有者與失效風險。高併發下最怕的是鎖住之後沒有安全釋放，或以為鎖保證了完整業務一致性。

原則上：

- 鎖應該短
- 鎖持有者要可辨識
- 鎖過期要可接受
- 業務上若能不用分散式鎖，通常應優先考慮更簡單的設計

## 【延伸】Go 端仍然要負責限流與取消

Redis 很快，不代表你可以不設邊界。Go 端仍然應該用 `context`、timeout、worker pool 或 rate limit 把壓力收斂起來。否則 goroutine 雖然便宜，排隊等待 Redis 回應的工作卻會越堆越多。

## 和 Go 教材的關係

這一章是 Redis 的實作邊界；如果你要先理解 Go 端為什麼會這樣設計，可以先回去看：

- [Go 並發模型總覽](../../go/04-concurrency/concurrency-model/)：先理解 goroutine 很便宜，但外部資源不是。
- [Go 進階：rate limiting 與背壓](../../go-advanced/01-concurrency-patterns/rate-limit/)：先看 Go 端怎麼把過量流量擋在入口。
- [Go 進階：共享狀態與複製邊界](../../go-advanced/01-concurrency-patterns/shared-state/)：先看快取資料與內部狀態如何切邊界。

## 小結

Go 服務處理 Redis 的核心原則是：client 共用、操作要短、pipeline 要有節制、熱點 key 要設計、cache miss 要防 stampede、鎖要保守使用。Redis 很適合高併發，但前提是你先替它設好邊界。
