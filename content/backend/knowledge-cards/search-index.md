---
title: "Search Index"
date: 2026-06-22
description: "說明搜尋索引如何承擔全文檢索、排序與查詢體驗"
weight: 146
tags: ["backend", "observability", "database"]
---

Search index 的核心概念是「為查詢體驗建立專用的讀取模型」。它擅長全文搜尋、排序、filter 與 facet，通常是 [derived state](/backend/knowledge-cards/source-of-truth/)、從正式資料源同步而來。

## 概念位置

Search index 是 [read model](/backend/knowledge-cards/read-model/) 的一種實作。正式狀態仍由 [source of truth](/backend/knowledge-cards/source-of-truth/) 管理（relational DB、document DB），search index 透過 CDC、event subscription 或 ETL 同步更新。概念上跟 [materialized view](/backend/knowledge-cards/materialized-view/) 類似 — 都是為特定查詢需求預先準備的資料形狀。

在觀測領域，log storage 的 search index（Elasticsearch / Loki 的 label index）承擔 log 查詢的效能。Index 的欄位選擇跟 cardinality 影響查詢延遲跟儲存成本，見 [4.1 log schema](/backend/04-observability/log-schema/)。

## 使用情境

商品搜尋、文件站搜尋、客服多條件檢索、log 查詢通常都需要 search index 提供低延遲查詢體驗。Elasticsearch、Algolia、Meilisearch、Typesense 是常見實作。

## 設計責任

設計時要定義索引更新延遲（source 變更到 index 可查的時間）、重建流程（index 損壞或 schema 改版時的 full reindex）、查詢語意（全文 vs 結構化 filter）與權限過濾（search 結果是否要按使用者權限過濾）。Index 是 derived state — 修復方式是 rebuild 而非直接修改。
