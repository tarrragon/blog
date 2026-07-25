---
title: "Keyset Pagination"
date: 2026-05-27
description: "用上一頁最後一筆的 key 當下一頁起點、避開 OFFSET 大表時的線性退化"
weight: 357
---

Keyset pagination（也稱 cursor pagination）的核心責任是讓大表分頁性能穩定在 O(LIMIT)、跟 offset 大小解耦。傳統 `LIMIT 20 OFFSET 10000` 在大表退化成「掃描 10020 行 + skip 10000 行」、是 O(OFFSET + LIMIT)；keyset 寫成 `WHERE id > last_seen_id LIMIT 20`、永遠是 O(LIMIT)、跟 offset 大小無關。跟 [query cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) 同屬大表查詢反模式修法、機制各自獨立。

## 概念位置

Keyset pagination 處於 SQL query 設計的「pagination 策略」維度、跟 [query cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) 是 sibling 反模式修法；它的查詢狀態要不要對外承諾成不透明 cursor、是另一張卡 [Pagination Cursor](/backend/knowledge-cards/pagination-cursor/) 承擔的契約面。對比：

| 策略         | 寫法                               | 複雜度          | 限制                               |
| ------------ | ---------------------------------- | --------------- | ---------------------------------- |
| OFFSET-based | `LIMIT 20 OFFSET 10000`            | O(offset+limit) | 大表線性退化、deep pagination 退化 |
| Keyset       | `WHERE id > last_seen_id LIMIT 20` | O(limit)        | 限於順序逐頁、跳頁需另設計         |

## 可觀察訊號與例子

該採用的訊號：排序欄位是 indexed + unique（或加 tiebreaker 確保唯一）、使用者操作是「逐頁前進」（next / load more）、大表（百萬 row 以上）需要分頁。Twitter timeline、Slack 訊息歷史、GitHub commit 列表都用 keyset。實測大表 deep pagination 場景 keyset 比 OFFSET 快數百倍 — OFFSET 100000 的 query 從秒級降到毫秒級。

## 設計責任

排序欄位若是非 unique（如 `created_at`）、用 `(created_at, id)` 複合條件確保穩定 — 缺 tiebreaker 時、重複值翻頁會跳過或重複資料。Cursor 編碼成 opaque token 給 client、避免暴露內部 ID 結構（也方便未來改 cursor 內容）。對「插入 / 刪除中翻頁」的行為比 OFFSET 穩定（OFFSET 在這類場景容易跳過或重複）。表小於 10000 行時 OFFSET 也快、保持簡單即可。Google 搜尋結果頁那種「跳到第 N 頁」需求要回到 OFFSET 或考慮重新設計使用者操作。
