---
title: "Keyset Pagination"
date: 2026-05-27
description: "用上一頁最後一筆的 key 當下一頁起點、避開 OFFSET 大表時的線性退化"
weight: 357
---

Keyset pagination（也稱 cursor pagination）用「上一頁最後一筆的 key 當下一頁起點」、取代傳統 `OFFSET` 分頁。差別在性能曲線：`OFFSET` 在大表退化成「掃描 N + OFFSET 行 + skip OFFSET 行」、是 O(OFFSET + LIMIT)；keyset 是 `WHERE id > last_seen_id LIMIT 20`、永遠是 O(LIMIT)、跟 offset 大小無關。是 [cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) 之外、大表查詢的另一個高頻反模式修法。

## 概念位置

Keyset pagination 處於 SQL query 設計的「pagination 策略」維度、跟 [cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) 同屬大表查詢的反模式修法但機制不同：cardinality 是 join 行數爆、keyset 是 offset 退化。比較：

| 策略         | 寫法                               | 複雜度          | 缺點                               |
| ------------ | ---------------------------------- | --------------- | ---------------------------------- |
| OFFSET-based | `LIMIT 20 OFFSET 10000`            | O(offset+limit) | 大表線性退化、不能 deep pagination |
| Keyset       | `WHERE id > last_seen_id LIMIT 20` | O(limit)        | 不能跳頁、必須順序逐頁             |

## 使用條件

Keyset pagination 適用的場景：

- 排序欄位是 indexed + unique（或加 tiebreaker 確保唯一）
- 使用者操作是「逐頁前進」（next / load more）、不是「跳到第 N 頁」
- 大表（百萬 row 以上）需要分頁

不適用：

- 使用者需要「跳到第 N 頁」、Goolge 搜尋結果頁那種 — keyset 沒有「第 N 頁」概念
- 排序欄位有重複值且無 tiebreaker — 可能漏 row 或重複
- 表很小（< 10000 行）— `OFFSET` 也快、不必複雜化

## 實作要點

- **Tiebreaker**：若排序欄位非 unique（如 created_at），用 `(created_at, id)` 複合條件確保穩定
- **方向**：通常用 `>` 取下一頁、`<` 取上一頁；DESC 排序時方向相反
- **Cursor 編碼**：把 last_seen key 編碼成 opaque cursor token 給 client、避免暴露內部 ID 結構
- **跨資料變更**：keyset 對「資料插入 / 刪除中翻頁」的行為比 OFFSET 穩定（OFFSET 可能跳過或重複）

## 反模式

- **OFFSET 在大表上 deep pagination**：`LIMIT 20 OFFSET 100000` 等於 scan 100020 行、是常見 production 性能事故
- **用 Keyset 但沒 tiebreaker**：重複的排序值會跳過 row
- **強迫 keyset 支援跳頁**：硬把「跳到第 N 頁」加上去、退化成 OFFSET、失去 keyset 優勢
