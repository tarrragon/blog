---
title: "Search Index"
date: 2026-06-22
description: "說明搜尋索引如何承擔全文檢索、排序與查詢體驗"
weight: 147
tags: ["backend", "observability", "database"]
---

Search index 的核心概念是「為查詢體驗建立專用的讀取模型」。它擅長全文搜尋、排序、filter 與 facet，通常是 [derived state](/backend/knowledge-cards/source-of-truth/)、從正式資料源同步而來。

## 跟其他概念的關係

Search index 是 [read model](/backend/knowledge-cards/read-model/) 的一種實作。正式狀態仍由 [source of truth](/backend/knowledge-cards/source-of-truth/) 管理（relational DB、document DB），search index 透過 CDC、event subscription 或 ETL 同步更新。概念上跟 [materialized view](/backend/knowledge-cards/materialized-view/) 類似 — 都是為特定查詢需求預先準備的資料形狀。

在觀測領域，log storage 的 search index（Elasticsearch / Loki 的 label index）承擔 log 查詢的效能。Index 的欄位選擇跟 cardinality 影響查詢延遲跟儲存成本，見 [4.1 log schema](/backend/04-observability/log-schema/)。

## 使用情境

商品搜尋、文件站搜尋、客服多條件檢索、log 查詢通常都需要 search index 提供低延遲查詢體驗。Elasticsearch、Algolia、Meilisearch、Typesense 是常見實作。

## 判斷條件與後果

Search index 是從 source 同步出來的 derived state，它的更新延遲、重建流程、查詢語意與權限過濾沒有定義時，各自產生一種錯的查詢結果。索引更新延遲（source 變更到 index 可查的時間）沒有定義時，搜尋結果跟正式資料源之間的差距沒有基準，無從判斷某次落後是否異常；沒有重建流程（index 損壞或 schema 改版時的 full reindex）時，index 只能就地修補，修補後的 index 跟 source 之間的差異無從核對；查詢語意（全文比對還是結構化 filter）沒有分清時，同一個查詢條件在兩種語意下回傳不同的結果集；search 結果沒有按使用者權限過濾時，使用者從搜尋結果看到他在正式頁面上無權讀取的資料。Index 的內容全部由 source 推導而來，所以 index 出錯時從 source rebuild，而非直接修改 index。
