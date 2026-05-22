---
title: "Logical Replication"
date: 2026-05-22
description: "說明以表為粒度解碼 row-level 變更的複製方式，對照 byte-level 的實體複製"
weight: 339
---

Logical Replication 的核心概念是以 table 或 publication 為粒度，把 row-level 變更解碼成邏輯事件再複製到下游，相對於整個 cluster byte-level 複製的實體複製。它讓跨版本、選擇性、跨系統的複製成為可能，代價是要處理 schema 漂移與 [Replication Slot](/backend/knowledge-cards/replication-slot/) 的保留壓力。它是 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 的常見基礎。

## 概念位置

Logical Replication 位在複製粒度光譜的一端。實體複製複製的是 storage 的 byte / page，整個 cluster 一起、版本綁定，適合 HA 與整體還原；logical replication 解碼成 row 事件、可選表、可跨版本，適合 CDC、跨系統同步與漸進遷移。它依賴 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/) 作為變更來源，用 [Replication Slot](/backend/knowledge-cards/replication-slot/) 追蹤進度。

## 可觀察訊號與例子

適合 logical replication 的訊號是只需要部分表、要跨大版本升級、或要把資料送到非同種系統。需要注意的訊號是 schema 變更：發佈端改 schema 時，訂閱端與下游 consumer 要協調，否則事件欄位對不上。它和實體複製是互補關係 — 許多系統同時用實體複製做 HA、用 logical replication 做資料整合。

## 設計責任

設計時要決定哪些表進入 logical replication、schema 變更如何在發佈端與訂閱端協調，以及 slot lag 的監控與告警。要明確它和實體複製各自承擔 HA 與資料整合的哪一塊。observability 要看 replication lag、slot 保留量與套用錯誤。
