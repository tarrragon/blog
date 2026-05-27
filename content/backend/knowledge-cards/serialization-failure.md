---
title: "Serialization Failure"
date: 2026-05-27
description: "SERIALIZABLE isolation 衝突偵測後 abort 的協議、SQL state 40001、application 必須包 retry loop"
weight: 367
---

Serialization failure 的核心概念是「SERIALIZABLE isolation 偵測到並行 transaction 衝突、把後到的 transaction abort、回傳 SQL state `40001`、要求 application 包 retry loop 重跑」。它是 serializable 跟弱 isolation 行為差異的關鍵介面、跟 [Isolation Level](/backend/knowledge-cards/isolation-level/) 共軸、retry 設計沒做好會升級成 [Retry Storm](/backend/knowledge-cards/retry-storm/)。

## 概念位置

Serialization failure 是跨 vendor 共通協議、不是單一資料庫的機制。CockroachDB（預設 SERIALIZABLE）、Spanner（read-write transaction）、PostgreSQL SSI（opt-in SERIALIZABLE）、Aurora DSQL 都會在偵測衝突時丟 `40001`。差別在 *衝突偵測時機*：PostgreSQL SSI 用 predicate lock 在 commit 階段偵測、CockroachDB 用 timestamp ordering + write intent 在衝突當下就 abort、Spanner 用 strict 2PL 在讀寫過程中 detect。對 application 來說、不管哪家、看到的都是同一個 error code、處理方式一致：rollback、backoff、重跑。

跟 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 一起設計 — transaction body 必須是 *冪等可重跑*、不能含「呼叫外部 API 扣款」這類無法重做的副作用。

## 可觀察訊號與例子

需要面對 serialization failure 的訊號是「同一段 application code 在 PostgreSQL READ COMMITTED 上從不失敗、遷到 CockroachDB / Spanner 後 retry rate 突然飆升」、或「serializable cluster 的 hot row 路徑 p99 latency 隨並行度線性惡化」。CockroachDB 從 PostgreSQL READ COMMITTED 遷移時、application 接管 retry contract 是必要工程、Cockroach Labs 官方推薦 `SAVEPOINT cockroach_restart` 寫法、讓整個 transaction 可以在 `ROLLBACK TO SAVEPOINT` 後重新進入。Spanner SDK 內建 retry loop、但開發者仍要保證 transaction body 冪等。

## 設計責任

設計 serializable workload 時必須先寫 retry policy：exponential backoff + jitter 避免 retry storm、max retry 限制避免 user-facing latency 拖垮、retry budget 接 circuit breaker。Application code 要把 transaction body 寫成可重入 — 跨 statement 的 in-memory state、外部 API call、非冪等寫入都要移出 transaction。沒寫 retry loop 等於把 serializable cluster 當 READ COMMITTED 用、衝突就直接拋例外給終端 user。Hot row 場景（同一筆庫存被千人搶）serialization failure 會持續存在、要靠 [Database Sharding](/backend/knowledge-cards/database-sharding/) 或 application-level 排隊解決、不是調大 retry 次數能擋。
