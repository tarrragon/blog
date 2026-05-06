---
title: "Data Completeness"
date: 2026-04-23
description: "說明資料是否完整到足以支持查詢、遷移與決策"
weight: 86
---


Data completeness 的核心概念是「資料是否完整到足以支持目標用途」。資料可以格式正確，但仍缺少必要筆數、欄位、時間範圍或關聯資料。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 概念位置

Completeness 是資料品質的一部分。Migration、backfill、報表、audit、搜尋索引與機器學習資料集都需要確認資料是否完整。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 可觀察訊號與例子

系統需要 completeness check 的訊號是資料遷移完成後仍可能缺漏。訂單資料搬遷時，除了 row count，也要確認 order items、付款紀錄、退款紀錄與狀態歷史是否完整。

## 設計責任

Completeness 檢查要包含總量、分群、時間範圍、關聯完整性與抽樣。結果應進入 [Migration Gate](/backend/knowledge-cards/migration-gate/)，並留下可重跑的查詢或報表。
