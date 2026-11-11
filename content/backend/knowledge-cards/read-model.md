---
title: "Read Model"
date: 2026-06-22
description: "說明為查詢場景建立的讀取模型，與正式狀態的責任分離"
weight: 151
tags: ["backend", "architecture", "database"]
---

Read model 的核心概念是「為特定查詢需求建立專用的資料形狀」。它跟正式狀態（[source of truth](/backend/knowledge-cards/source-of-truth/)）的責任分離 — 正式狀態為寫入的正確性最佳化，read model 為讀取的效率與體驗最佳化。

## 跟其他概念的關係

Read model 是 [CQRS](/backend/knowledge-cards/cqrs/) 的讀取面產物。在 CQRS 架構中，write model 跟 read model 各自獨立，read model 透過同步機制（event handler、CDC、定期刷新）從 write model 更新。

Read model 的來源可以是 [projection](/backend/knowledge-cards/projection/)（從 [event log](/backend/knowledge-cards/event-log/) 持續推算）、[materialized view](/backend/knowledge-cards/materialized-view/)（從 SQL 查詢預計算）、CDC consumer（從 row change 同步到搜尋索引）或批次 ETL（定期從 OLTP 匯出到 analytics store）。不同的來源機制有不同的更新延遲跟維護成本。

在觀測領域，[recording rule](/backend/knowledge-cards/recording-rule/) 跟 [rollup](/backend/knowledge-cards/rollup/) 扮演類似 read model 的角色 — 從 raw time series 預計算聚合結果，讓 dashboard 讀取預聚合資料而非重算 raw data。

## 判斷條件與後果

Read model 的同步延遲、重建流程、欄位語意與查詢邊界，各自決定它出錯時的後果。同步延遲沒有約定可接受的上限時，查詢結果落後 write model 多久都沒有判斷依據；重建流程沒有準備時，read model 損壞或 schema 變更之後只剩直接修資料一條路，而那正是下一段說的分岔來源。欄位語意沒有寫明時，同名欄位在兩邊的定義不同，查詢方拿 read model 的值當成 write model 的定義判讀；查詢邊界沒有寫明時，read model 被拿去支援它沒有設計來支援的查詢，回傳的結果不完整。

Read model 是派生狀態，修復方式是「砍掉重建」而非直接修改。把 read model 當正式狀態修改會導致 write model 跟 read model 分岔、後續同步覆蓋修改。
