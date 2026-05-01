---
title: "PostgreSQL"
date: 2026-05-01
description: "多用途 OLTP 主流關聯式資料庫"
weight: 1
---

PostgreSQL 是 backend 預設關聯式資料庫的安全選擇、生態完整、SQL 功能豐富、MVCC 與 transaction 模型穩定。多數新專案沒特殊需求時的 default。

## 適用場景

- 多用途 OLTP、複雜查詢、JOIN 與 window function
- 需要 strong consistency 與 transaction 保證
- JSON / JSONB 半結構化資料
- 進階特性：full-text search、PostGIS、邏輯複製

## 不適用場景

- 極高寫入吞吐（>10K QPS 單機）— 考慮 sharding 或專用 OLTP DB
- key-value 簡單查詢且需要 P99 latency 嚴格控制 — 用 DynamoDB / Redis
- 大規模 OLAP — 用 ClickHouse / BigQuery / Snowflake

## 跟其他 vendor 的取捨

- vs `mysql`：PostgreSQL 功能更豐富、JSON / GIS / window 完整；MySQL 在簡單 query 與 Vitess 分片生態更成熟
- vs `aurora`：Aurora 是 managed PostgreSQL/MySQL、犧牲一些 PostgreSQL 高級特性換 storage scale
- vs `cockroachdb`：CockroachDB 提供水平擴展與跨區一致性、但 latency 與功能相容度有差距

## 預計實作話題

- Connection pool（pgBouncer / PgCat）
- 高可用（streaming replication / Patroni / pg_auto_failover）
- Logical decoding / CDC（Debezium）
- Schema migration（Flyway / Liquibase / golang-migrate）
- 索引與 query 優化
