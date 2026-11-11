---
title: "Isolation Level"
date: 2026-04-23
description: "說明資料庫交易隔離級別如何影響並發讀寫結果"
weight: 17
---

Isolation level 的核心概念是「交易彼此看見資料變更的規則」。隔離級別越高，越能降低並發異常；同時也可能增加鎖競爭、等待與重試成本。 可先對照 [Jitter](/backend/knowledge-cards/jitter/)。

## 跟其他概念的關係

隔離級別處理的是同一份資料被多個交易同時讀寫時的行為。常見問題包括 dirty read、non-repeatable read、phantom read、lost update 與 write skew。不同資料庫的預設隔離與實作細節不同。 可先對照 [Jitter](/backend/knowledge-cards/jitter/)。

## 可觀察訊號與例子

系統需要討論隔離級別的訊號是高併發更新同一類資料。兩個使用者同時搶最後一件庫存、兩個 worker 同時認領同一筆工作、兩個後台操作同時修改權限，都需要明確的一致性策略。

## 判斷條件與後果

同一份資料被多個交易同時讀寫時，可以接受哪些並發結果（兩個使用者同時搶最後一件庫存，是否容許超賣）決定了該用哪一種工具：transaction、lock、unique constraint、optimistic concurrency 或 retry。沒有先定義可接受的結果就選隔離級別時，可能選得太低而留下 lost update 或 write skew，也可能選得太高，付出鎖競爭、等待與重試的成本，換到的保證卻不是業務需要的那一種。隔離級別只規定交易彼此看見哪些變更，而不同資料庫的預設隔離與實作細節不同，只靠它表達的業務規則換一個資料庫就可能改變行為；寫成狀態機與唯一約束的正式規則落實在資料上，換了資料庫或隔離級別也照樣成立。
