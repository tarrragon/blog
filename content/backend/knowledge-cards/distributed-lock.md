---
title: "Distributed Lock"
date: 2026-05-27
description: "跨機器跨 process 的互斥鎖、用 lease 機制處理 holder 失效"
weight: 351
---

Distributed lock 的核心責任是讓分散式系統中多個 process 對共享資源做互斥存取。跟單機 mutex 不同、distributed lock 必須處理 holder 失效（process crash、network partition）導致鎖無法釋放的問題 — 解法是 lease（租約）：持鎖 process 必須定期 renew、否則鎖自動過期。跟 [consensus protocol](/backend/knowledge-cards/consensus-protocol/) 是上下層關係 — 多數 production distributed lock 的底層依賴 consensus 保證跨節點一致。

## 概念位置

Distributed lock 處於分散式系統的協調控制層、跟 [consensus protocol](/backend/knowledge-cards/consensus-protocol/) 是上下層關係（lock 服務底層通常用 consensus 實作）。常見實作載體：

- **Redis SET NX + EX**：簡單 lease lock、但跨 master failover 可能丟鎖（Redlock 算法是嘗試強化但仍有爭議）
- **ZooKeeper / Etcd / Consul**：consensus 底層、提供更強的一致性保證、適合 leader election 跟長期鎖
- **資料庫層**：PostgreSQL advisory lock、MySQL `GET_LOCK()` — 跟業務 transaction 同源、但跟 DB primary 綁定

## 使用場景

主要適用「跨 process 互斥」的場景：

- **Leader election**：多 worker 競爭單一 leader 角色執行排程任務
- **資源獨佔**：避免兩個 process 同時處理同一筆訂單、扣同一筆庫存
- **分散式 cache build**：避免 cache miss 時多個 process 同時打 origin（per [cache stampede](/backend/knowledge-cards/cache-stampede/) 防護）
- **Migration / cleanup job**：確保任何時刻只有一個 instance 在跑

## 不適用場景

- **高頻短鎖**（每秒上萬次 acquire）：lease + renew 的 overhead 高、用 partition / sharding 避免共享資源更好
- **長交易**：lease 期間做長操作會撞 lease timeout、應該縮短 critical section
- **正確性要求極高的金融場景**：Redis-based lock 不保證 strong consistency、應該用底層有 consensus 的方案

## 失敗模式

- **Lease 過期但 process 還活著**：clock drift、long GC pause 都會讓 process 自認持鎖、實際 lease 已過期被別人搶走 — 需要 fencing token 保證寫入時被拒絕
- **Renew 失敗未察覺**：renew loop 在 background、若 network 卡住沒及時拋錯、process 會自信操作其實無鎖的資源
- **跨 master failover 丟鎖**：Redis master 切換時、新 master 可能沒有舊 master 的鎖狀態
