---
title: "Full-Text Search"
date: 2026-04-23
description: "說明全文檢索如何處理關鍵字匹配、語言分析與排序"
weight: 161
---

Full-text search 的核心概念是「對文本內容做可擴展檢索」。它支援分詞、相關性排序與關鍵字查詢。

## 概念位置

通常由 [search index](../search-index/) 提供，適合文件、商品描述與知識庫查詢。

## 設計責任

設計時要定義語言分析規則、索引更新延遲與查詢範圍，避免搜尋結果與產品預期落差。
