---
title: "Range Sharding"
date: 2026-05-27
description: "分散式 SQL 把 key space 切成可自動 split / merge 的 range、每個 range 自己的 consensus group、application 透明"
weight: 363
---

Range sharding 的核心概念是「distributed SQL 把整個 key space 依 key 順序切成多個 range、每個 range 有自己的 consensus group 跟 replica 分布、容量逼近 split 上限就自動分裂、application 看到的只是 SQL table」。它的責任是讓資料分散變成系統內建透明機制、不需要 application 端設計 shard key。可先對照 [Database Sharding](/backend/knowledge-cards/database-sharding/)。

## 跟其他概念的關係

Range sharding 出現在 CockroachDB / Spanner 等 distributed SQL、跟 [Partition](/backend/knowledge-cards/partition/) 必須區分 — partition 卡承擔事件流 / KV 風格的 hash partition 語意、range sharding 是 distributed SQL 系統內透明的 range-based 切分、兩者語意不同。跟 [Database Sharding](/backend/knowledge-cards/database-sharding/) 區分：後者是 application-level 由開發者選 shard key 跟設計 routing、range sharding 是系統自動 split / merge 不需要 shard key。跟 [Table Partitioning](/backend/knowledge-cards/table-partitioning/) 區分：PostgreSQL declarative partition 是 single-node table 內的 partition、range sharding 是跨節點分散 + consensus 一起的機制。

## 可觀察訊號與例子

需要 range sharding 概念的訊號是「設計 distributed SQL schema 時、誤把 KV 的 shard key 思維搬過來」。[Netflix CockroachDB](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 揭露 range 預設 ~512MB 自動 split 的機制：380+ cluster / 最大單區 60 nodes / 26.5 TB、不需要 application 端做 shard 設計。[Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 也用類似機制、跟 interleaved table 配合做 parent-child 物理 co-location。

## 判斷條件與後果

Range sharding 下的 hot range 由 primary key 的順序造成。連續寫入 monotonic key（例如 timestamp）時，新的寫入都進到 key space 尾端的同一個 range，那個 range 的 consensus group 處理全部寫入，原因是 range 依 key 順序切分；range sharding 沒有讓 application 設定 shard key 的地方，所以解法是讓 primary key 有 entropy（例如改用 UUID 或加 hash prefix）。range split 雖然自動，split 的過程是一次 ops event，會引發短期的 p99 spike，所以變更窗口避開 split。多 region 部署時，range 的 replica placement 由 locality config 決定，沒有配置時 replica 不會自動放到合規 region，資料可能存放在合規要求以外的 region。
