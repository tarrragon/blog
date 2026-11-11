---
title: "Follower Read"
date: 2026-05-27
description: "分散式 SQL 從 non-voting replica 讀 closed timestamp 之前的資料、不參與 Raft commit、低 latency 但 read-after-write 場景仍可能 stale"
weight: 367
---

Follower read 的核心概念是「distributed SQL 把 read 從 leaseholder 路徑分流到 non-voting replica、讀的是 closed timestamp 之前已確定不會被改寫的快照」。它的責任是讓跨 region 部署仍能在本地讀到資料、不用付每次 read 都跨 region 找 leaseholder 的 RTT、代價是只能讀稍 stale 的資料。可先對照 [Stale Read](/backend/knowledge-cards/stale-read/)。

## 跟其他概念的關係

Follower read 出現在 CockroachDB / Spanner 等跨 region distributed SQL、跟 [Stale Read](/backend/knowledge-cards/stale-read/) 是現象與機制的對應 — stale read 是症狀、follower read 是 *有意設計* 換 latency 的機制。跟 [Fallback Read](/backend/knowledge-cards/fallback-read/) 區分：後者是 failure 時的降級路徑、follower read 是常態低 latency 路徑、兩者觸發條件不同。跟 [Read Write Split](/backend/knowledge-cards/read-write-split/) 區分：後者是 application-level 把 read 導到 replica、follower read 是 distributed SQL 系統內機制、application 透明、跟 voting / non-voting replica 配置綁定。

## 可觀察訊號與例子

需要 follower read 的訊號是「跨 region distributed SQL、read p99 卡在跨 region RTT 上、但業務可容忍秒級 stale」。[Netflix CockroachDB](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 揭露 region survival 配置下的 follower read 機制：voting replica 跨 region 參與 commit、non-voting replica 只 serve follower read；`REGIONAL BY ROW` + `SURVIVE REGION FAILURE` 配合時、其他 region 有 non-voting replica 提供本地 follower read。[Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 在 SDK 層提供 `bounded_staleness(t)` 選項、容忍 t 秒、可讀最近的本地 replica。

## 判斷條件與後果

Follower read 的判斷條件是每一類讀取能容忍多舊的資料。餘額查詢、剛寫完的訂單這類 strong consistency read 走 follower read 時，讀到的是 closed timestamp 之前的快照，使用者看不到自己剛寫進去的值；dashboard、reporting、風控分析這類容忍 stale 的讀取走 follower read，省下每次跨 region 找 leaseholder 的 RTT。staleness 的上界是 closed timestamp 推進的延遲（通常數秒），這個值來自系統推進 closed timestamp 的機制，應用端調整快取秒數改變不了它，所以它寫進 SLO 當成讀取新鮮度的承諾。Follower read 是常態的低延遲路徑，failure 時的降級由 [fallback read](/backend/knowledge-cards/fallback-read/) 負責；每多一個 region 的 non-voting replica 就多一份 storage，replica 配置的成本隨 region 數增加。
