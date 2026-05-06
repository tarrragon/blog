---
title: "Poison Message"
date: 2026-04-23
description: "說明特定訊息內容如何穩定造成 consumer 失敗"
weight: 65
---


Poison message 的核心概念是「某一則訊息的內容會穩定造成 consumer 失敗」。它可能是格式錯誤、schema 不相容、資料狀態衝突、權限不足或程式 bug 觸發條件。 可先對照 [Post-Incident Review](/backend/knowledge-cards/post-incident-review/)。

## 概念位置

Poison message 是 queue pipeline 的隔離對象。系統要把它從主要處理路徑移開，讓正常訊息繼續前進，同時保留診斷資料給人工或修復流程。 可先對照 [Post-Incident Review](/backend/knowledge-cards/post-incident-review/)。

## 可觀察訊號與例子

系統需要 poison message 判斷的訊號是同一訊息每次投遞都失敗。新版 producer 多送一個 consumer 還不支援的 enum 值，可能讓舊版 consumer 持續失敗。

## 設計責任

Poison message 要進入 dead-letter，並保留 payload 摘要、schema version、錯誤類型、consumer version、correlation id 與重放條件。修復後才應 replay。
