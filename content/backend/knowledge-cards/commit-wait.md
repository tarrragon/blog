---
title: "Commit Wait"
date: 2026-05-27
description: "Spanner external consistency 的核心機制 — read-write transaction 拿 commit timestamp s 後等到 TT.after(s) 才 ACK、wait ≈ 2ε、付 latency tax 換 commit 順序 = real-time 順序"
weight: 364
---

Commit wait 的核心概念是「read-write transaction 拿到 commit timestamp `s` 後、Spanner 不立刻回 ACK、而是等到 `TT.after(s)` 確定為真（即 wall clock 必然已過 s）才回 ACK、wait 時間約 2ε」。它的責任是用一段固定 latency 支出換取「transaction commit timestamp 全序 = real-time 順序」這個 external consistency 保證。可先對照 [TrueTime](/backend/knowledge-cards/truetime/)。

## 概念位置

Commit wait 出現在 Spanner 系列產品、是 [TrueTime](/backend/knowledge-cards/truetime/) API 跟 [External Consistency](/backend/knowledge-cards/external-consistency/) 之間的橋接機制 — TrueTime 給帶 ε 不確定區間的時間 API、commit wait 是 *用它撐 external consistency 的具體實作*。跟 [Latency Budget](/backend/knowledge-cards/latency-budget/) 互補：commit wait 是無法 scale away 的固定 latency 支出、要當設計初期就寫進預算、不是運維後才補。

## 可觀察訊號與例子

需要 commit wait 判讀的訊號是「Spanner write latency 拆解時、commit_latencies p99 跟 ε 一起平移」。[9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 揭露 commit wait 機制：Spanner 設 `s = TT.now().latest` 後等 `TT.after(s)`、wait ≈ 2ε（從拿 s 那刻起算）；ε 通常 1-7ms（Spanner vendor docs / 2012 OSDI 論文揭露範圍、非 case 直接揭露 production 分布）、所以 commit wait 通常落在 2-14ms。voting region 越分散、ε 上限越高、commit wait 越長。

## 設計責任

設計時要把 commit wait 當成「Spanner 寫入路徑的固定 latency 稅」、不是可優化掉的成本。region layout 決策直接影響 commit wait — voting region 散布越廣、ε 上限越高、commit wait 越長。read-only transaction 可用 `exact_staleness` / `bounded_staleness` 避開 commit wait、適合 reporting / analytics；strong consistency read 要付完整 commit wait + quorum cost、要主動分流。把寫入路徑當「等 commit wait → quorum 已 ack」兩段同步來推 SLO、不是只看 quorum latency 就估完。
