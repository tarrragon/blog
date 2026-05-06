---
title: "Dual Write"
date: 2026-04-23
description: "說明同一變更同時寫入兩個系統時的一致性風險"
weight: 83
---


Dual write 的核心概念是「同一業務變更同時寫入兩個系統」。它常用在 migration、新舊系統並行、資料同步與服務拆分期間。 可先對照 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 概念位置

Dual write 是高風險一致性模式。兩個寫入目標很難共享同一個 transaction，因此可能出現一邊成功、一邊失敗，或兩邊順序不同。 可先對照 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 可觀察訊號與例子

系統需要 dual write 風險評估的訊號是 migration 期間新舊資料都要保持更新。會員資料同時寫舊資料庫與新資料庫時，任一邊 timeout 都可能造成資料分裂。

## 設計責任

Dual write 要搭配 outbox、reconcile、correctness check、重試與 fallback plan。設計文件應說明哪一邊是 source of truth，以及不一致時如何修復。
