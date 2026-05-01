---
title: "MongoDB"
date: 2026-05-01
description: "Document database 代表、彈性 schema 與 sharding"
weight: 4
---

MongoDB 是 document database 的代表、schema-less 寫入彈性高、原生 sharding 與 replica set。適合 schema 演進快、半結構化資料密集的場景。

## 適用場景

- Schema 演進快、半結構化 / nested 資料
- 內容管理、產品目錄、user profile 等聚合型資料
- 需要原生 sharding 與 replica set
- 早期 prototype 不確定 schema 時

## 不適用場景

- 強一致 multi-document transaction（雖然支援但效能不如 RDBMS）
- 複雜 JOIN / 關聯資料
- 嚴格 schema 與型別約束需求

## 跟其他 vendor 的取捨

- vs `postgresql` JSONB：PostgreSQL JSONB 提供 document 能力 + relational；MongoDB 在 sharding 與運維工具更原生
- vs `dynamodb`：DynamoDB 是 managed key-value、scaling 模型不同

## 預計實作話題

- Replica set 與 election
- Sharding 策略（hashed / ranged / zone）
- Index 與 aggregation pipeline
- MongoDB Atlas 託管選項
- Schema validation
