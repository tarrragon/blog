---
title: "Distributed Lock"
date: 2026-05-27
description: "跨機器跨 process 的互斥鎖、用 lease 機制處理 holder 失效"
weight: 351
---

Distributed lock 的核心責任是讓分散式系統中多個 process 對共享資源做互斥存取。比單機 mutex 多一層責任：要處理 holder 失效（process crash、network partition）後鎖的自動釋放 — 解法是 lease（租約）：持鎖 process 必須定期 renew、未 renew 時鎖自動過期。底層通常依賴 [consensus protocol](/backend/knowledge-cards/consensus-protocol/) 保證跨節點對「誰持鎖」達成一致、跟 [leader election](/backend/knowledge-cards/leader-election/) 區分在「資源互斥 vs 角色互斥」兩種使用情境。

## 概念位置

Distributed lock 處於分散式協調控制層、底層通常依賴 [consensus protocol](/backend/knowledge-cards/consensus-protocol/)。常見實作載體：

- **Redis SET NX + EX**：簡單 lease lock、Redlock 算法嘗試強化但仍有爭議
- **ZooKeeper / Etcd / Consul**：consensus 底層、提供強一致性保證、適合長期鎖
- **資料庫層**：PostgreSQL advisory lock、MySQL `GET_LOCK()` — 跟業務 transaction 同源、但跟 DB primary 綁定

## 可觀察訊號與例子

典型使用情境包含分散式 cache build（cache miss 時讓單一 process 打 origin、配合 [cache stampede](/backend/knowledge-cards/cache-stampede/) 防護）、migration / cleanup job 確保單一 instance 執行、確保兩個 worker 處理不同訂單。實測 Redis lock acquire latency 毫秒級、Etcd / ZK 跨 region 可達 10-50ms — 高頻短鎖通常改用 partition / sharding、是更省 lock 的設計。

## 設計責任

Fencing token 是必備設計 — 用單調遞增 token 在舊 holder 跟新 holder 並存時、讓資源側拒絕舊 holder 的寫入、防範 clock drift 或 long GC pause 導致的隱性鎖失效。Renew loop 要在 background 確認 renew 成功、若 network 卡住未及時拋錯、process 會自信操作其租約已失效的資源。Lease 期間應縮短 critical section、保持操作時間遠小於 lease timeout。
