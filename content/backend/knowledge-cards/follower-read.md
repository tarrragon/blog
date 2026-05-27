---
title: "Follower Read"
date: 2026-05-27
description: "分散式 SQL 從 non-voting replica 讀 closed timestamp 之前的資料、不參與 Raft commit、低 latency 但 read-after-write 場景仍可能 stale"
weight: 366
---

Follower read 的核心概念是「distributed SQL 把 read 從 leaseholder 路徑分流到 non-voting replica、讀的是 closed timestamp 之前已確定不會被改寫的快照」。它的責任是讓跨 region 部署仍能在本地讀到資料、不用付每次 read 都跨 region 找 leaseholder 的 RTT、代價是只能讀稍 stale 的資料。可先對照 [Stale Read](/backend/knowledge-cards/stale-read/)。

## 概念位置

Follower read 出現在 CockroachDB / Spanner 等跨 region distributed SQL、跟 [Stale Read](/backend/knowledge-cards/stale-read/) 是現象與機制的對應 — stale read 是症狀、follower read 是 *有意設計* 換 latency 的機制。跟 [Fallback Read](/backend/knowledge-cards/fallback-read/) 區分：後者是 failure 時的降級路徑、follower read 是常態低 latency 路徑、兩者觸發條件不同。跟 [Read Write Split](/backend/knowledge-cards/read-write-split/) 區分：後者是 application-level 把 read 導到 replica、follower read 是 distributed SQL 系統內機制、application 透明、跟 voting / non-voting replica 配置綁定。

## 可觀察訊號與例子

需要 follower read 的訊號是「跨 region distributed SQL、read p99 卡在跨 region RTT 上、但業務可容忍秒級 stale」。[9.C40 Netflix CockroachDB](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 揭露 region survival 配置下的 follower read 機制：voting replica 跨 region 參與 commit、non-voting replica 只 serve follower read；`REGIONAL BY ROW` + `SURVIVE REGION FAILURE` 配合時、其他 region 有 non-voting replica 提供本地 follower read。[9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 在 SDK 層提供 `bounded_staleness(t)` 選項、容忍 t 秒、可讀最近的本地 replica。

## 設計責任

設計時要把 follower read 跟 read 業務分流綁在一起 — strong consistency read（餘額查詢、剛寫完的訂單）走 leaseholder 路徑、容忍 stale 的 read（dashboard / reporting / 風控分析）走 follower read。不要把 follower read 當 failover 機制、它不是 — failover 是 fallback read 的責任。配置 non-voting replica 時要評估 storage cost、每多一個 region 多一份 storage。closed timestamp 推進延遲（通常數秒）就是 follower read 的 staleness 上界、要寫進 SLO、不是「快取秒數可調」。
