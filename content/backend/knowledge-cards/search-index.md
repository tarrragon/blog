---
title: "Search Index"
date: 2026-04-23
description: "說明搜尋索引如何承擔全文檢索、排序與查詢體驗"
weight: 146
---


Search index 的核心概念是「為查詢體驗建立專用讀取模型」。它擅長全文搜尋、排序、filter 與 facet，通常不是正式寫入來源。 可先對照 [Source of Truth](/backend/knowledge-cards/source-of-truth/)。

## 概念位置

Search index 常由資料庫或事件流同步更新，承擔讀取查詢責任；正式狀態仍由 [source of truth](/backend/knowledge-cards/source-of-truth/) 管理。

## 可觀察訊號與例子

例如商品搜尋、文件站搜尋、客服多條件檢索，通常都需要 search index 來提供低延遲查詢體驗。

## 設計責任

設計時要定義索引更新延遲、重建流程、查詢語意與權限過濾，避免把查詢層與主資料責任混在一起。
