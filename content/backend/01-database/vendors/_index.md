---
title: "資料庫 Vendor 清單"
date: 2026-05-01
description: "後端資料庫實作時的常用選擇，預先建立引用路徑"
weight: 90
tags: ["backend", "database", "vendor"]
---

本清單列出 backend 服務實作會選用的 database vendor / platform。每個 vendor 一個資料夾，先建定位與取捨骨架，實作話題隨後續擴充。

## T1 vendor（全部完整 page）

- [postgresql](/backend/01-database/vendors/postgresql/) — 多用途 OLTP 主流、Aurora / Cosmos / Spanner / CockroachDB / Aurora DSQL 的相容目標
- [mysql](/backend/01-database/vendors/mysql/) — 高併發網路服務、Vitess / PlanetScale 分片生態、GitHub / Shopify 規模驗證
- [sqlite](/backend/01-database/vendors/sqlite/) — embedded、test fixture、+ 新興 Cloudflare D1 / Turso 場景
- [mongodb](/backend/01-database/vendors/mongodb/) — document DB 代表、Atlas 跨雲 managed
- [dynamodb](/backend/01-database/vendors/dynamodb/) — AWS managed KV、9 個 09 case（Amazon Ads、Tixcraft、Zoom、Capcom、Disney+ 等）
- [aurora](/backend/01-database/vendors/aurora/) — AWS managed PostgreSQL / MySQL、5 個 09 case（DraftKings、Standard Chartered、Netflix、FanDuel）
- [spanner](/backend/01-database/vendors/spanner/) — GCP 全球分散式 strong-consistency OLTP、TrueTime
- [cosmosdb](/backend/01-database/vendors/cosmosdb/) — Azure 全球分散式 multi-model、5 consistency levels
- [cockroachdb](/backend/01-database/vendors/cockroachdb/) — 分散式 SQL、Spanner 的開源 / 跨雲替代

## 後續擴充

- T2 候選：planetscale-vitess、tidb、yugabytedb、neon、supabase、azure-sql-hyperscale
- T3 候選：firestore、couchdb、clickhouse（OLAP）、scylladb（Cassandra-compat）
