---
title: "Poison Message"
date: 2026-04-23
description: "說明特定訊息內容如何穩定造成 consumer 失敗"
weight: 66
---

Poison message 的核心概念是「某一則訊息的內容會穩定造成 consumer 失敗」。它可能是格式錯誤、schema 不相容、資料狀態衝突、權限不足或程式 bug 觸發條件。 可先對照 [Post-Incident Review](/backend/knowledge-cards/post-incident-review/)。

## 跟其他概念的關係

Poison message 是 queue pipeline 的隔離對象。系統要把它從主要處理路徑移開，讓正常訊息繼續前進，同時保留診斷資料給人工或修復流程。 可先對照 [Post-Incident Review](/backend/knowledge-cards/post-incident-review/)。

## 可觀察訊號與例子

系統需要 poison message 判斷的訊號是同一訊息每次投遞都失敗。新版 producer 多送一個 consumer 還不支援的 enum 值，可能讓舊版 consumer 持續失敗。

## 判斷條件與後果

Poison message 留在主 queue 時，每次投遞都失敗，後面的正常訊息跟著停住，所以它被移進 dead-letter。進了 dead-letter 之後，修復的人要判斷它為什麼失敗、重放會不會再失敗：少了 schema version 與 consumer version，分不出是不是新版 producer 送了舊版 consumer 不支援的值；少了錯誤類型與 payload 摘要，分不出是格式錯誤、資料狀態衝突還是程式 bug；少了 correlation id，追不回產生這則訊息的請求；少了重放條件，不知道修到什麼程度才能重放。根因修好之前 replay 時，這則訊息會以同樣的原因再失敗一次，回到 dead-letter。
