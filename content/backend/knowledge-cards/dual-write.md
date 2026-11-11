---
title: "Dual Write"
date: 2026-04-23
description: "說明同一變更同時寫入兩個系統時的一致性風險"
weight: 84
---

Dual write 的核心概念是「同一業務變更同時寫入兩個系統」。它常用在 migration、新舊系統並行、資料同步與服務拆分期間。 可先對照 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 跟其他概念的關係

Dual write 是高風險一致性模式。兩個寫入目標很難共享同一個 transaction，因此可能出現一邊成功、一邊失敗，或兩邊順序不同。 可先對照 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 可觀察訊號與例子

系統需要 dual write 風險評估的訊號是 migration 期間新舊資料都要保持更新。會員資料同時寫舊資料庫與新資料庫時，任一邊 timeout 都可能造成資料分裂。

## 判斷條件與後果

Dual write 的兩個寫入目標不共享 transaction，一邊成功、一邊失敗的狀態會出現，判斷的對象是它出現之後系統能否發現並修復。沒有指定哪一邊是 source of truth 時，兩邊資料不同就判斷不了該以哪一邊為準，修復無從開始。只在請求當下同步寫兩邊、沒有 outbox 時，寫完第一邊之後 process 中斷，第二邊的寫入就此遺失，原因是待寫的變更只存在記憶體裡；沒有 reconcile 與 correctness check 時，這類分裂要等使用者看到錯的資料才被發現。重試補得回暫時失敗的那一邊，但兩邊的寫入順序可能因此不同，原因是兩個系統各自決定寫入的先後。Migration 期間新系統出錯而沒有 fallback plan 時，退不回只寫舊系統的狀態。
