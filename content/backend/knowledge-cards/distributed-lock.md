---
title: "Distributed Lock"
date: 2026-05-27
description: "跨機器跨 process 的互斥鎖、用 lease 機制處理 holder 失效"
weight: 352
---

Distributed lock 的核心責任是讓分散式系統中多個 process 對共享資源做互斥存取。比單機 mutex 多一層責任：要處理 holder 失效（process crash、network partition）後鎖的自動釋放 — 解法是 lease（租約）：持鎖 process 必須定期 renew、未 renew 時鎖自動過期。底層通常依賴 [consensus protocol](/backend/knowledge-cards/consensus-protocol/) 保證跨節點對「誰持鎖」達成一致、跟 [leader election](/backend/knowledge-cards/leader-election/) 區分在「資源互斥 vs 角色互斥」兩種使用情境。已經有共用的 PostgreSQL 時，排程互斥這類需求常改用資料庫的 [Advisory Lock（建議鎖）](/backend/knowledge-cards/advisory-lock/)。

## 跟其他概念的關係

Distributed lock 處於分散式協調控制層、底層通常依賴 [consensus protocol](/backend/knowledge-cards/consensus-protocol/)。常見實作載體：

- **Redis SET NX + EX**：簡單 lease lock、Redlock 算法嘗試強化但仍有爭議
- **ZooKeeper / Etcd / Consul**：consensus 底層、提供強一致性保證、適合長期鎖
- **資料庫層**：PostgreSQL advisory lock、MySQL `GET_LOCK()` — 跟業務 transaction 同源、但跟 DB primary 綁定

## 可觀察訊號與例子

典型使用情境包含分散式 cache build（cache miss 時讓單一 process 打 origin、配合 [cache stampede](/backend/knowledge-cards/cache-stampede/) 防護）、migration / cleanup job 確保單一 instance 執行、確保兩個 worker 處理不同訂單。實測 Redis lock acquire latency 毫秒級、Etcd / ZK 跨 region 可達 10-50ms — 高頻短鎖通常改用 partition / sharding、是更省 lock 的設計。

## 判斷條件與後果

Lease 過期而原 holder 還沒察覺時，系統裡同時有兩個 process 認為自己持鎖。舊 holder 遇到 long GC pause 或 clock drift，恢復之後繼續寫入，共享資源被兩邊同時改動，原因是 lease 的過期只記錄在鎖服務上，舊 holder 自己不知道；fencing token 讓鎖服務每次發出單調遞增的 token，資源側拒絕 token 比已見過的更小的寫入，舊 holder 的寫入因此被擋下。Background 的 renew 失敗而沒有拋錯時（network 卡住、renew 請求逾時），process 繼續操作一份租約已經失效的資源，處在同一種雙 holder 狀態。Critical section 的執行時間接近 lease timeout 時，任何一次延遲都可能讓 lease 在操作途中過期，所以 critical section 的時間要遠小於 lease timeout。
