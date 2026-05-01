---
title: "資料庫 Vendor 清單"
date: 2026-05-01
description: "後端資料庫實作時的常用選擇，預先建立引用路徑"
weight: 90
---

本清單列出 backend 服務實作會選用的 database vendor / platform。每個 vendor 一個資料夾，先建定位與取捨骨架，實作話題隨後續擴充。

## T1 vendor

- [postgresql](/backend/01-database/vendors/postgresql/) — 多用途 OLTP 主流
- [mysql](/backend/01-database/vendors/mysql/) — 高併發網路服務、PlanetScale / Vitess 生態
- [sqlite](/backend/01-database/vendors/sqlite/) — embedded、CLI、test fixture
- [mongodb](/backend/01-database/vendors/mongodb/) — document DB 代表
- [dynamodb](/backend/01-database/vendors/dynamodb/) — AWS managed key-value、cell-based scaling
- [cockroachdb](/backend/01-database/vendors/cockroachdb/) — 分散式 SQL、跨區強一致
- [aurora](/backend/01-database/vendors/aurora/) — AWS managed PostgreSQL / MySQL

## 後續擴充

- T2 候選：spanner、planetscale-vitess、tidb、yugabytedb、neon、supabase
- T3 候選：firestore、couchdb、clickhouse（OLAP）、scylladb（Cassandra-compat）
