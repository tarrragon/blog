---
title: "Data Lifecycle"
tags: ["資料生命週期", "Data Lifecycle"]
date: 2026-04-23
description: "說明資料從建立、使用、保留到刪除的責任邊界"
weight: 13
---


資料生命週期的核心概念是「資料從建立到移除之間的責任安排」。後端系統要知道資料何時建立、誰能修改、保存多久、何時封存、何時刪除，以及刪除後哪些副本也要同步處理。 可先對照 [Data Masking](/backend/knowledge-cards/data-masking/)。

## 概念位置

資料生命週期連接產品需求、成本與資安。訂單資料可能需要長期保存以支援稽核；debug log 可能只保留數天；匯出檔案可能需要短期下載期限與自動清除。 可先對照 [Data Masking](/backend/knowledge-cards/data-masking/)。

## 可觀察訊號與例子

系統需要資料生命週期設計的訊號是資料量持續成長、使用者要求刪除資料、稽核要求保存證據，或觀測資料成本快速上升。聊天訊息、付款紀錄、trace、報表檔案的保留策略通常不同。

## 設計責任

生命週期設計要定義保留期限、刪除流程、封存策略、備份影響、權限與 audit。資料移除時也要處理 cache、search index、object storage、log 與第三方系統副本。
