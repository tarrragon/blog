---
title: "Profile Diff"
date: 2026-05-12
description: "對比兩次 profile（如 release candidate vs baseline）找出 hottest 變化"
weight: 236
---

Profile diff 的核心概念是「兩次 profile 取得後、用差分視覺化找出 *相對變化最大* 的 code path」。比看絕對值更能定位退化原因。可先對照 [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)。

## 概念位置

Profile diff 的常見實作：Brendan Gregg 的 differential flame graph、Pyroscope diff、Datadog Continuous Profiler diff、Parca compare。輸入是兩個 profile（同樣 sampling 條件下取得）、輸出是「新版本比舊版本多花了多少 CPU / memory / lock time」。可先對照 [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)。

## 可觀察訊號與例子

需要 profile diff 的訊號是「release 後 latency 退化、不知道是哪段 code 拖累」。對應案例：[Netflix Aurora 統一](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 層統一後 profile 變單純、profile diff 更容易識別 application 層的退化來源。

## 設計責任

Profile diff 必須在 *相同負載 + 相同硬體 + 相同 sampling rate* 下取得、否則結果無意義。看「相對變化幅度」而非絕對 CPU%。Diff 結果通常需要工程師判讀、不能純自動化判斷退化是否可接受 — 因為「多花 20% CPU 但 throughput 多 50%」可能是 *好變化*。
