---
title: "Isolation Level"
date: 2026-04-23
description: "說明資料庫交易隔離級別如何影響並發讀寫結果"
weight: 16
---

Isolation level 的核心概念是「交易彼此看見資料變更的規則」。隔離級別越高，越能降低並發異常；同時也可能增加鎖競爭、等待與重試成本。

## 概念位置

隔離級別處理的是同一份資料被多個交易同時讀寫時的行為。常見問題包括 dirty read、non-repeatable read、phantom read、lost update 與 write skew。不同資料庫的預設隔離與實作細節不同。

## 可觀察訊號與例子

系統需要討論隔離級別的訊號是高併發更新同一類資料。兩個使用者同時搶最後一件庫存、兩個 worker 同時認領同一筆工作、兩個後台操作同時修改權限，都需要明確的一致性策略。

## 設計責任

設計時要先定義可接受的並發結果，再選擇 transaction、lock、unique constraint、optimistic concurrency 或 retry。隔離級別是工具之一，業務層仍需要狀態機與唯一約束表達正式規則。
