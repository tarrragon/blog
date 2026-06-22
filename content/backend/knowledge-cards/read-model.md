---
title: "Read Model"
date: 2026-06-22
description: "說明為查詢場景建立的讀取模型，與正式狀態的責任分離"
weight: 150
tags: ["backend", "architecture", "database"]
---

Read model 的核心概念是「為特定查詢需求建立專用的資料形狀」。它跟正式狀態（[source of truth](/backend/knowledge-cards/source-of-truth/)）的責任分離 — 正式狀態為寫入的正確性最佳化，read model 為讀取的效率與體驗最佳化。

## 概念位置

Read model 是 [CQRS](/backend/knowledge-cards/cqrs/) 的讀取面產物。在 CQRS 架構中，write model 跟 read model 各自獨立，read model 透過同步機制（event handler、CDC、定期刷新）從 write model 更新。

Read model 的來源可以是 [projection](/backend/knowledge-cards/projection/)（從 [event log](/backend/knowledge-cards/event-log/) 持續推算）、[materialized view](/backend/knowledge-cards/materialized-view/)（從 SQL 查詢預計算）、CDC consumer（從 row change 同步到搜尋索引）或批次 ETL（定期從 OLTP 匯出到 analytics store）。不同的來源機制有不同的更新延遲跟維護成本。

在觀測領域，[recording rule](/backend/knowledge-cards/recording-rule/) 跟 [rollup](/backend/knowledge-cards/rollup/) 扮演類似 read model 的角色 — 從 raw time series 預計算聚合結果，讓 dashboard 讀取預聚合資料而非重算 raw data。

## 設計責任

設計 read model 時要定義同步延遲（read model 落後 write model 多久可以接受）、重建流程（read model 損壞或 schema 變更時如何從頭重建）、欄位語意（read model 的欄位定義跟 write model 可能不同）與查詢邊界（這個 read model 能回答什麼問題、不能回答什麼問題）。

Read model 是派生狀態，修復方式是「砍掉重建」而非直接修改。把 read model 當正式狀態修改會導致 write model 跟 read model 分岔、後續同步覆蓋修改。
