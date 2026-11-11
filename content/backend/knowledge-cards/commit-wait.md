---
title: "Commit Wait"
date: 2026-05-27
description: "Spanner external consistency 的核心機制 — read-write transaction 拿 commit timestamp s 後等到 TT.after(s) 才 ACK、wait ≈ 2ε、付 latency tax 換 commit 順序 = real-time 順序"
weight: 365
---

Commit wait 的核心概念是「read-write transaction 拿到 commit timestamp `s` 後、Spanner 不立刻回 ACK、而是等到 `TT.after(s)` 確定為真（即 wall clock 必然已過 s）才回 ACK、wait 時間約 2ε」。它的責任是用一段固定 latency 支出換取「transaction commit timestamp 全序 = real-time 順序」這個 external consistency 保證。可先對照 [TrueTime](/backend/knowledge-cards/truetime/)。

## 跟其他概念的關係

Commit wait 出現在 Spanner 系列產品、是 [TrueTime](/backend/knowledge-cards/truetime/) API 跟 [External Consistency](/backend/knowledge-cards/external-consistency/) 之間的橋接機制 — TrueTime 給帶 ε 不確定區間的時間 API、commit wait 是 *用它撐 external consistency 的具體實作*。跟 [Latency Budget](/backend/knowledge-cards/latency-budget/) 互補：commit wait 是無法 scale away 的固定 latency 支出、要當設計初期就寫進預算、不是運維後才補。

## 可觀察訊號與例子

需要 commit wait 判讀的訊號是「Spanner write latency 拆解時、commit_latencies p99 跟 ε 一起平移」。[Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 揭露 commit wait 機制：Spanner 設 `s = TT.now().latest` 後等 `TT.after(s)`、wait ≈ 2ε（從拿 s 那刻起算）；ε 通常 1-7ms（Spanner vendor docs / 2012 OSDI 論文揭露範圍、非 case 直接揭露 production 分布）、所以 commit wait 通常落在 2-14ms。voting region 越分散、ε 上限越高、commit wait 越長。

## 判斷條件與後果

Commit wait 是 Spanner 每一筆 read-write transaction 寫入路徑上的固定 latency，長度約 2ε，調校 application 或加機器都不會讓它變短。寫入路徑的 SLO 只用 quorum latency 推估時，估出來的延遲少了 commit wait 這一段；把寫入當成「等 commit wait」與「等 quorum ack」兩段同步的時間相加，推出的才是實際的寫入延遲。ε 隨 region layout 改變：voting region 散布越廣，ε 上限越高，commit wait 越長，所以 region layout 的選擇同時決定了寫入延遲的下限。讀取路徑的成本依一致性要求而不同：read-only transaction 用 `exact_staleness` 或 `bounded_staleness` 讀稍舊的快照時不付 commit wait，適合 reporting 與 analytics；strong read 不付 commit wait（commit wait 是寫入端在回報提交之前的等待），它付的是另一種等待：讀取的時間戳要等副本的 safe time 追上，必要時向 leader 確認之前的寫入都已提交，所以延遲比讀稍舊快照高，只有要求讀到最新寫入的路徑才分流到它。
