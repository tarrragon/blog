---
title: "Facet Query"
date: 2026-04-23
description: "說明分面查詢如何提供分類統計與篩選體驗"
weight: 162
---

Facet query 的核心概念是「在搜尋結果上提供可聚合的分類維度」。它讓使用者能快速依品牌、分類、價格區間等條件縮小結果。

## 概念位置

常與 [search index](../search-index/) 與 [full-text search](../full-text-search/) 搭配，提升查詢互動性。

## 設計責任

設計時要定義分面欄位、聚合成本與更新策略，避免高成本聚合拖慢查詢。

