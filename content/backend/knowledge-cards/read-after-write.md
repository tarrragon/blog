---
title: "Read-After-Write Consistency"
date: 2026-05-22
description: "說明寫入後能否立即讀到該筆寫入的一致性保證"
weight: 341
---

Read-After-Write Consistency 的核心概念是一個明確的保證：寫入成功後，後續讀取能立即看到這筆寫入。它讓「送出後馬上檢視」這類操作有正確的結果。它和泛指讀到舊資料的 [Stale Read](/backend/knowledge-cards/stale-read/) 相對，並常和 [Session Consistency](/backend/knowledge-cards/session-consistency/) 一起出現。

## 概念位置

Read-After-Write 位在一致性保證光譜上、比 eventual consistency 強的一端。它通常是 session 範圍的保證：同一使用者的寫入，自己後續讀得到。在用 [Read-Write Split](/backend/knowledge-cards/read-write-split/) 的架構下它要特別設計，因為讀取分流到有 [Replication Lag](/backend/knowledge-cards/replication-lag/) 的 replica 時，剛寫入的資料可能還沒同步。

## 可觀察訊號與例子

需要 read-after-write 的訊號是使用者送出資料後會立刻看結果：下單後看訂單、發文後看貼文、改設定後回設定頁。這些路徑讀到舊狀態會被當成「資料遺失」的 bug。提供保證的常見做法是讓這類讀取走 primary、加 lag guard、或在 session 內 pin 到能看到自己寫入的來源。

## 設計責任

設計時要列出哪些讀取路徑需要 read-after-write 保證，並為它們選實作方式。要明確保證的範圍：是同一 session、跨 session、還是全域。observability 要能量到分流到 replica 的讀取中，有多少落在 lag 窗口內而可能讀到舊資料。
