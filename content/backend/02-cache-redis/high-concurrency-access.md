---
title: "2.1 高併發下的 Redis 讀寫邊界"
date: 2026-04-22
description: "說明高併發服務如何共用 Redis client、控制 pipeline 與避免 cache stampede"
weight: 1
---

Redis 在後端服務裡常扮演 cache、session、counter、dedup、presence 或輕量協調層。它通常比 SQL 更適合高併發短操作，但前提是 client、連線池、pipeline 與 key 設計都受控。高併發下的 Redis 仍然會遇到 [hot key](../../knowledge-cards/hot-key/)、快取穿透、stampede、過大 pipeline 與不當鎖設計。

## 本章目標

學完本章後，你將能夠：

1. 理解為什麼 Redis client 應該共用
2. 分辨單鍵操作、pipeline、[transaction](../../knowledge-cards/transaction/) 與 Lua 的邊界
3. 了解高併發下的 [cache stampede](../../knowledge-cards/cache-stampede/) 與 hot key 問題
4. 用 `context` 與 [timeout](../../knowledge-cards/timeout/) 保護 Redis 呼叫
5. 把 Redis 用在適合的資料角色，並保留正式狀態來源

---

## 【觀察】Redis 呼叫大多是短網路 I/O

應用端對 Redis 的操作通常是短小但頻繁的網路請求。這代表真正影響效能的往往是 RTT、連線重用、批次送出與 key 設計。

所以高併發時，重點是控制 Redis 邊界：

- 用同一個 client 共用連線池
- 對獨立操作使用合理的 pipeline
- 熱門資料要避免集中到單一 key

## 【判讀】client 共用比每次建立更重要

Redis client 的核心設計通常就是讓應用共用同一個實例。每個 request 都 new client，會把連線管理成本、握手成本與資源回收問題全部放大。

高併發服務通常會採用：

- process 啟動時建立一個 Redis client
- request handler、worker、service layer 共用它
- 所有操作都帶 `context`
- timeout 與取消由上層傳入

## 【策略】pipeline 用來節省 RTT

pipeline 的價值是把多個獨立命令一次送出，減少往返次數。它很適合：

- 多個彼此獨立的讀取
- 批次寫入
- 一次更新多個 cache key

pipeline 的核心限制是批次大小仍要受控。太大的 pipeline 會帶來：

- 內存壓力
- 回應延遲變大
- 單次失敗影響更多操作

## 【判讀】原子性需求要分清楚

Redis 的很多操作本身就可以很快，但原子性與一致性需要額外設計。當需求需要多個資料變更形成同一個結果時，才應該考慮：

- 單鍵原子操作
- transaction
- Lua script
- 由上層做去重或補償

transaction 應服務明確的一致性需求，cache 寫入也應維持輔助狀態定位。Redis 很常是輔助狀態，真正的 [source of truth](../../knowledge-cards/source-of-truth/) 通常還是在 SQL 或 domain store。

## 【策略】cache stampede 與 hot key 要先處理

高併發快取最常見的兩個問題，是大量 goroutine 同時 [miss](../../knowledge-cards/cache-hit-miss/) 同一筆資料，以及大量流量打到同一個 key。

### cache stampede

當 cache miss 發生時，如果每個 request 都直接回源查 DB，會把後端放大成更大的壓力。常見的處理方式包括：

- 設定合理 [TTL](../../knowledge-cards/ttl/)
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
- counter / [rate limit](../../knowledge-cards/rate-limit/)
- presence / online state
- dedup / [idempotency](../../knowledge-cards/idempotency/) key
- lightweight [queue](../../knowledge-cards/queue/) / stream

每一種角色都有不同容錯方式。counter、presence 和 cache 的失敗語意各自不同，因此需要依資料角色選擇處理策略。

## 【策略】分散式 lock 要謹慎使用

Redis 常被拿來做 distributed lock，但這類機制要非常清楚 lease、過期、持有者與失效風險。高併發下最怕的是鎖住之後沒有安全釋放，或以為鎖保證了完整業務一致性。

原則上：

- 鎖應該短
- 鎖持有者要可辨識
- 鎖過期要可接受
- 業務上若能不用分散式鎖，通常應優先考慮更簡單的設計

## 【延伸】語言端仍然要負責限流與取消

Redis 很快，但應用端仍然要設計邊界。語言端應使用 timeout、cancellation、[worker pool](../../knowledge-cards/worker-pool/)、rate limit 或 [backpressure](../../knowledge-cards/backpressure/) 把壓力收斂起來；否則排隊等待 Redis 回應的工作會越堆越多。

## 跨語言適配評估

Redis 高併發邊界會受語言 runtime 影響。Thread-based runtime 要管理 client pool 與 blocking command；async runtime 要確認 Redis client 不會阻塞 event loop；輕量 task runtime 要限制同時呼叫 Redis 的工作數量。動態語言要特別控制 cache value schema 與序列化格式；強型別語言要避免把內部型別直接當成跨服務 cache [contract](../../knowledge-cards/contract/)。

## 小結

高併發服務處理 Redis 的核心原則是：client 共用、操作要短、pipeline 要有節制、熱點 key 要設計、cache miss 要防 stampede、鎖要保守使用。Redis 很適合高併發，但前提是服務先替它設好邊界。
