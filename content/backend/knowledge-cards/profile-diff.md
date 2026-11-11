---
title: "Profile Diff"
date: 2026-05-12
description: "對比兩次 profile（如 release candidate vs baseline）找出 hottest 變化"
weight: 237
---

Profile diff 的核心概念是「兩次 profile 取得後、用差分視覺化找出 *相對變化最大* 的 code path」。比看絕對值更能定位退化原因。可先對照 [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)。

## 跟其他概念的關係

Profile diff 的常見實作：Brendan Gregg 的 differential flame graph、Pyroscope diff、Datadog Continuous Profiler diff、Parca compare。輸入是兩個 profile（同樣 sampling 條件下取得）、輸出是「新版本比舊版本多花了多少 CPU / memory / lock time」。可先對照 [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)。

## 可觀察訊號與例子

需要 profile diff 的訊號是「release 後 latency 退化、不知道是哪段 code 拖累」。對應案例：[Netflix Aurora 統一](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 層統一後 profile 變單純、profile diff 更容易識別 application 層的退化來源。

## 判斷條件與後果

兩份 profile 的負載、硬體或 sampling rate 有任一項不同時，差分裡混進了取樣條件的差異，變化無法歸因到程式碼的改動，結果沒有意義。條件相同時，看的是各 code path 的相對變化幅度，因為絕對的 CPU% 會隨負載整體移動，相對變化才指得出新版本多花資源的是哪一段。某段多花了資源也可能是用資源換吞吐量：「多花 20% CPU 但 throughput 多 50%」是好的變化，這要對照吞吐量才判斷得出來，所以 diff 的結果通常由工程師判讀，單靠差分數字無法自動決定退化是否可接受。
