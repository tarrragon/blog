---
title: "Logical Replication"
date: 2026-05-22
description: "說明以表為粒度解碼 row-level 變更的複製方式，對照 byte-level 的實體複製"
weight: 340
---

Logical Replication 的核心概念是以 table 或 publication 為粒度，把 row-level 變更解碼成邏輯事件再複製到下游，相對於整個 cluster byte-level 複製的實體複製。它讓跨版本、選擇性、跨系統的複製成為可能，代價是要處理 schema 漂移與 [Replication Slot](/backend/knowledge-cards/replication-slot/) 的保留壓力。它是 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 的常見基礎。

## 跟其他概念的關係

Logical Replication 位在複製粒度光譜的一端。實體複製複製的是 storage 的 byte / page，整個 cluster 一起、版本綁定，適合 HA 與整體還原；logical replication 解碼成 row 事件、可選表、可跨版本，適合 CDC、跨系統同步與漸進遷移。它依賴 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/) 作為變更來源，用 [Replication Slot](/backend/knowledge-cards/replication-slot/) 追蹤進度。

## 可觀察訊號與例子

適合 logical replication 的訊號是只需要部分表、要跨大版本升級、或要把資料送到非同種系統。需要注意的訊號是 schema 變更：發佈端改 schema 時，訂閱端與下游 consumer 要協調，否則事件欄位對不上。它和實體複製是互補關係 — 許多系統同時用實體複製做 HA、用 logical replication 做資料整合。

## 判斷條件與後果

Logical replication 以表或 publication 為複製範圍，schema 與訂閱端的進度各自是失效的來源。發佈端改了 schema 而訂閱端與下游 consumer 沒有一起改時，事件欄位對不上，訂閱端套用時出錯。訂閱端落後或停止時，[Replication Slot](/backend/knowledge-cards/replication-slot/) 仍保留尚未送出的 [WAL](/backend/knowledge-cards/write-ahead-log/)，主庫的磁碟用量持續上升，原因是 slot 要保證訂閱端回來時還拿得到中間的變更；replication lag、slot 保留量與套用錯誤沒有監控時，這段累積要到磁碟告警才被發現。HA 由實體複製負責、資料整合由 logical replication 負責時，兩邊的失效互不影響；只用 logical replication 做 HA 時，沒有納入 publication 的表在切換之後不在新主庫上。
