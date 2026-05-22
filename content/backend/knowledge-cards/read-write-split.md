---
title: "Read-Write Split"
date: 2026-05-22
description: "說明讀寫流量如何分流到 primary 與 replica，以及它引入的一致性責任"
weight: 325
---

Read-Write Split 的核心概念是把寫入導向 primary、把讀取導向一個或多個 replica，用 replica 擴展讀取容量。它讓讀多寫少的服務把壓力分散開，而不必全部集中在 primary，代價是 replica 有 [Replication Lag](/backend/knowledge-cards/replication-lag/)，剛寫入的資料可能還沒同步。它和 [Connection Pool](/backend/knowledge-cards/connection-pool/)、[Transaction Pooling](/backend/knowledge-cards/transaction-pooling/) 一起決定連線怎麼分配；判斷讀到舊資料的後果時要接回 [Stale Read](/backend/knowledge-cards/stale-read/)。

## 概念位置

Read-Write Split 位在 application 與資料庫拓撲之間的路由層。它可以由 proxy、driver 或 application 自己實作；路由規則要分辨 write、一般 read、交易內讀取與需要強一致的讀取（例如 SELECT ... FOR UPDATE）。它和 [Replication Lag](/backend/knowledge-cards/replication-lag/) 直接耦合 — lag 越大，分流到 replica 的讀取看到舊資料的窗口越長。

## 可觀察訊號與例子

適合 read-write split 的訊號是 primary 的讀取壓力遠大於寫入、且多數讀取可以接受秒級延遲的資料。要特別處理的是「寫入後立刻讀」的流程：使用者送出訂單後馬上看訂單列表、後台改完權限馬上驗證，這些 read-after-write 路徑分到 replica 會讀到舊狀態。常見做法是讓這類路徑強制走 primary，或加一層 lag guard。

## 設計責任

設計時要定義路由規則、哪些讀取必須走 primary、交易內讀取如何 pin 在同一連線、以及 replica lag 超標時的降級策略。session 一致性要寫清楚：同一使用者的 read-after-write 是否保證。observability 要看 primary 與 replica 的讀寫分佈、replica lag，以及被 lag guard 擋回 primary 的比例。
