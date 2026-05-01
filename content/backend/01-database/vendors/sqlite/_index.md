---
title: "SQLite"
date: 2026-05-01
description: "Embedded SQL、CLI / desktop / test fixture"
weight: 3
---

SQLite 是嵌入式關聯式資料庫、無 server process、單檔儲存、零維運成本。適合 embedded、CLI 工具、test fixture、輕量服務、邊緣節點本地狀態。

## 適用場景

- 嵌入式應用（mobile / desktop / IoT / CLI）
- 測試 fixture / 整合測試 ephemeral DB
- 單機輕量服務、低 QPS 需求
- 本地快取 / 設定儲存

## 不適用場景

- 多 writer 高併發（writer 互斥鎖限制）
- 需跨機共享狀態
- 需要複雜 user / 權限管理

## 跟其他 vendor 的取捨

- vs `postgresql` / `mysql`：SQLite 是 embedded、無伺服器；功能子集
- vs LiteFS / Cloud SQLite：分散式 SQLite 變體（如 Turso / LiteFS）為 T2 候選

## 預計實作話題

- WAL mode 與並發優化
- Schema migration in embedded
- 測試 ephemeral DB pattern
- LiteFS / Litestream（replication / backup）
