---
title: "Read-Write Split"
date: 2026-05-22
description: "說明讀寫流量如何分流到 primary 與 replica，以及它引入的一致性責任"
weight: 326
---

Read-Write Split 的核心概念是把寫入導向 primary、把讀取導向一個或多個 replica，用 replica 擴展讀取容量。它讓讀多寫少的服務把壓力分散開，而不必全部集中在 primary，代價是 replica 有 [Replication Lag](/backend/knowledge-cards/replication-lag/)，剛寫入的資料可能還沒同步。它和 [Connection Pool](/backend/knowledge-cards/connection-pool/)、[Transaction Pooling](/backend/knowledge-cards/transaction-pooling/) 一起決定連線怎麼分配；判斷讀到舊資料的後果時要接回 [Stale Read](/backend/knowledge-cards/stale-read/)。

## 跟其他概念的關係

Read-Write Split 位在 application 與資料庫拓撲之間的路由層。它可以由 proxy、driver 或 application 自己實作；路由規則要分辨 write、一般 read、交易內讀取與需要強一致的讀取（例如 SELECT ... FOR UPDATE）。它和 [Replication Lag](/backend/knowledge-cards/replication-lag/) 直接耦合 — lag 越大，分流到 replica 的讀取看到舊資料的窗口越長。

## 可觀察訊號與例子

適合 read-write split 的訊號是 primary 的讀取壓力遠大於寫入、且多數讀取可以接受秒級延遲的資料。要特別處理的是「寫入後立刻讀」的流程：使用者送出訂單後馬上看訂單列表、後台改完權限馬上驗證，這些 read-after-write 路徑分到 replica 會讀到舊狀態。常見做法是讓這類路徑強制走 primary，或加一層 lag guard。路由放在應用程式、ORM 或代理時各自的規則（交易內的讀取、同一請求剛寫入之後的讀取、手寫 SQL 送哪裡），以及 GORM、Laravel、Django 的實際行為，見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈讀寫分離與多個資料庫：連線的路由由哪一層決定〉。

## 判斷條件與後果

Read-write split 的路由規則決定每一種讀取會不會讀到舊資料。交易內的讀取被分到 replica 時，交易裡剛寫入的資料在 replica 上還看不到，原因是 replica 落後 primary，所以交易內讀取 pin 在同一條連線；SELECT ... FOR UPDATE 這類需要強一致的讀取走 primary。同一使用者的 read-after-write 是否保證沒有寫清楚時，寫入後立刻讀的路徑可能分到 replica、讀到舊狀態。replica lag 超過門檻而沒有降級策略時，所有分到 replica 的讀取一起變舊；有 lag guard 時這些讀取被擋回 primary，primary 的負載跟著上升，所以 primary 與 replica 的讀寫分佈、replica lag 與擋回 primary 的比例要一起觀測，才看得出擋回的量是否接近 primary 的容量。
