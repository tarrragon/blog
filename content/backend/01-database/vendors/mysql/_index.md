---
title: "MySQL"
date: 2026-05-01
description: "高併發網路服務常用關聯式資料庫、Vitess / PlanetScale 分片生態"
weight: 2
---

MySQL 是大型網路服務的常見選擇、簡單 query 效能與分片生態（Vitess / PlanetScale）成熟。GitHub / Shopify / Slack / Facebook 等大規模服務的核心 OLTP 多採 MySQL。

## 適用場景

- 高併發、簡單 query 為主的 OLTP
- 需要水平分片（Vitess / PlanetScale 生態）
- 既有 MySQL 生態工具鏈（gh-ost / pt-online-schema-change）
- 強一致 transaction 但容忍部分 SQL 功能缺失

## 不適用場景

- 需要 PostgreSQL 等級的 SQL / JSON / GIS 功能
- 極端 OLAP query

## 跟其他 vendor 的取捨

- vs `postgresql`：見 PostgreSQL 篇
- vs `aurora`：Aurora MySQL 是 managed 版本、storage layer 重寫
- vs `planetscale-vitess`（T2）：原生 MySQL vs Vitess 託管的取捨

## 預計實作話題

- Replication topology（async / semi-sync / GTID）
- Online schema change（gh-ost / pt-online-schema-change）
- Sharding（Vitess）
- Orchestrator failover
- Connection pool 管理
