---
title: "Cross-Region Quorum"
date: 2026-05-27
description: "multi-region distributed SQL 強制 voting replica 跨 region、commit 等多 region quorum ack、跨洲 RTT 物理硬限"
weight: 372
---

Cross-region quorum 的核心概念是「multi-region distributed SQL（Spanner multi-region instance、CockroachDB region survival）強制 voting replica 跨 region 分布、write commit 必須等多 region quorum ack」。它跟 [Quorum](/backend/knowledge-cards/quorum/) 同源（後者是抽象機制）、但承擔 *跨 region 情境下被物理光速限定的 latency tax* 這個獨立語意 — 是 distributed SQL line-rate scaling 上無法 scale away 的固定支出、跟 [Latency Budget](/backend/knowledge-cards/latency-budget/) 共軸、跟 [Commit Wait](/backend/knowledge-cards/commit-wait/) 是相鄰但獨立的物理 cost。

## 跟其他概念的關係

Cross-region quorum 跟相鄰卡片有清楚的角色分工 — [Quorum](/backend/knowledge-cards/quorum/) 是抽象機制（多數 ack 即可 commit）、[Latency Budget](/backend/knowledge-cards/latency-budget/) 是把跨 region RTT 寫進 SLO 的決策框架、[Commit Wait](/backend/knowledge-cards/commit-wait/) 是 Spanner TrueTime 的另一段獨立延遲、不能混算同一個 latency 數字。

Cross-region quorum 的 latency 由 voting replica 之間的網路 RTT 主導、跟 instance config 強相關：

- Regional（單 region 多 zone）：voting 在同 region 內、quorum RTT < 5ms
- Dual-region（同大陸）：跨大陸內、quorum RTT 10-30ms
- Multi-region（跨洲）：跨大陸或跨洲、quorum RTT 100-200ms

跨洲 100-200ms 是物理光速下界、不是 vendor SLA 不夠好 — Spanner / CockroachDB 同樣硬限。常見誤讀是把這 100-200ms 寫成「Spanner commit wait」、實際 commit wait 是 TrueTime 不確定區間導致的另一段 2-14ms 等待、跟 cross-region quorum 是兩個獨立的物理 cost、不能混用一個 latency 數字解釋兩者。

## 可觀察訊號與例子

需要面對 cross-region quorum 的訊號是「multi-region distributed SQL 的 write p99 latency 鎖在 100-200ms、不管怎麼 tune client / cache / node size 都壓不下來」。對應情境：Spanner 跨洲 multi-region instance 揭露的工程數量級（依 voting region 配置變化、不是 SLA 承諾）；CockroachDB `SURVIVE REGION FAILURE` 強制 voting replica 散布到多 region、保 region 級故障 RPO=0 但 commit latency 直接吃跨 region RTT。Application 端的訊號是「跨洲 write 的 p99 跟 single-region 比是 10-20 倍、但 read（透過 [Follower Read](/backend/knowledge-cards/follower-read/)）p99 接近 single-region」。

## 判斷條件與後果

Cross-region quorum 的延遲由 voting replica 之間的 RTT 決定，跨洲配置的 100-200ms 是光速給的下界，調 client、cache 或 node size 都壓不下來。選了跨洲 multi-region config，每一次寫入都付這筆延遲，換到的是 region 級故障時 RPO=0，所以 instance config 的選擇決定兩種 workload 的處境。寫入密集而不需要 region survival 的 workload 選 multi-region 時，付了跨洲延遲卻用不到它換來的存活能力，而 regional config 的 quorum RTT 在 5ms 以內。確實需要跨 region 強一致的 workload，write latency budget 從 single-region 的 10ms 等級變成跨洲的 100-200ms，原本的 SLO 守不住，SLO 因此要跟業務重新協商。拿 100-200ms 做 capacity planning 的前提是自家 instance 確實是跨洲 multi-region：dual-region 的 quorum RTT 是 10-30ms，套錯基線時容量估算差到接近一個數量級。RTO=0／RPO=0 的成本記在 write latency 上而不在帳單上，sizing 文件只記費用時看不到這筆成本。
