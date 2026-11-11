---
title: "Keyset Pagination"
date: 2026-05-27
description: "用上一頁最後一筆的 key 當下一頁起點、避開 OFFSET 大表時的線性退化"
weight: 358
---

Keyset pagination 的核心責任是讓大表分頁性能穩定在 O(LIMIT)、跟 offset 大小解耦。傳統 `LIMIT 20 OFFSET 10000` 在大表退化成「掃描 10020 行 + skip 10000 行」、是 O(OFFSET + LIMIT)；keyset 寫成 `WHERE id > last_seen_id LIMIT 20`、永遠是 O(LIMIT)、跟 offset 大小無關。跟 [query cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) 同屬大表查詢反模式修法、機制各自獨立。業界常把它跟 cursor-based pagination（接續標記分頁）混稱；兩者在不同層：keyset 是定位機制，接續標記是對外的表示法，見 [Pagination Cursor](/backend/knowledge-cards/pagination-cursor/)，cursor 這個字的其他意思見 [Cursor](/backend/knowledge-cards/cursor/)。

## 跟其他概念的關係

Keyset pagination 處於 SQL query 設計的「pagination 策略」維度、跟 [query cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) 是 sibling 反模式修法；它的查詢狀態要不要對外承諾成不透明的接續標記（opaque cursor）、是另一張卡 [Pagination Cursor](/backend/knowledge-cards/pagination-cursor/) 承擔的契約面。對比：

| 策略         | 寫法                               | 複雜度          | 限制                               |
| ------------ | ---------------------------------- | --------------- | ---------------------------------- |
| OFFSET-based | `LIMIT 20 OFFSET 10000`            | O(offset+limit) | 大表線性退化、deep pagination 退化 |
| Keyset       | `WHERE id > last_seen_id LIMIT 20` | O(limit)        | 限於順序逐頁、跳頁需另設計         |

## 可觀察訊號與例子

該採用的訊號：排序欄位是 indexed + unique（或加 tiebreaker 確保唯一）、使用者操作是「逐頁前進」（next / load more）、大表（百萬 row 以上）需要分頁。Twitter timeline、Slack 訊息歷史、GitHub commit 列表都用 keyset。實測大表 deep pagination 場景 keyset 比 OFFSET 快數百倍 — OFFSET 100000 的 query 從秒級降到毫秒級。

## 判斷條件與後果

排序欄位不是 unique 時（例如 `created_at`），同一個值的幾筆資料跨在頁界上，只用 `created_at > last_seen` 接續會跳過或重複其中幾筆；用 `(created_at, id)` 的複合條件加上 tiebreaker，接續的位置才唯一。接續標記編碼成 opaque token 交給 client 時，client 看不到內部 ID 的結構，之後改變接續標記的內容也不影響 client。翻頁期間有資料插入或刪除時，keyset 比 OFFSET 穩定，原因是 keyset 從上一頁最後一筆的值接下去，OFFSET 依位置計數，前面多一筆或少一筆就跳過或重複。表小於 10000 行時 OFFSET 掃過的行數少，速度也快，維持 OFFSET 比較簡單。介面需要「跳到第 N 頁」時（Google 搜尋結果頁那種），keyset 只能從上一頁接續，這個需求要回到 OFFSET，或重新設計使用者操作。
