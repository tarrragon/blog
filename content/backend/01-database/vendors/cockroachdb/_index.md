---
title: "CockroachDB"
date: 2026-05-01
description: "分散式 SQL、跨區強一致、PostgreSQL 線協議相容"
weight: 6
---

CockroachDB 是分散式 SQL database、PostgreSQL wire protocol 相容、原生跨區強一致（Raft consensus）。適合需要水平擴展與多區可用性的 SQL 場景。

## 適用場景

- 跨區 / 多 region 強一致 SQL
- 需要水平擴展但仍要 SQL 與 transaction
- Geo-partitioning（資料駐留）需求
- PostgreSQL 相容過渡

## 不適用場景

- 單區、流量適中、PostgreSQL 已足夠
- 對 latency 敏感的高頻 single-region 寫入（共識成本）
- 大量 PostgreSQL 進階特性依賴（部分不相容）

## 跟其他 vendor 的取捨

- vs `postgresql`：CockroachDB 自動分散；PostgreSQL 需手動 sharding
- vs `spanner`（T2）：類似定位、Spanner 是 GCP managed；CockroachDB 可自管或 cloud

## 預計實作話題

- Raft consensus 與 latency 取捨
- Geo-partitioning 設計
- PostgreSQL 相容性邊界
- 從 PostgreSQL 遷移路徑
- CockroachDB Cloud
