---
title: "模組四：架構邊界與事件系統"
date: 2026-04-22
description: "用事件驅動架構拆解事件來源、處理流程、狀態邊界與即時推送"
weight: 4
---

架構邊界的核心目標是讓每個元件只承擔一種責任。事件來源負責接收外部訊號，normalize 階段負責轉成內部事件，processor 負責套用規則，repository 負責保存狀態真相，publisher 負責把結果送出去。

事件驅動不是把所有東西都丟進 channel。Go 的事件系統需要明確的型別、清楚的擁有者、可測的狀態轉移，以及能在多來源輸入下維持一致的處理流程。

本模組承接入門篇的 practical 與 refactoring：前面學會新增事件、建立 repository port、拆 handler、整理 domain package；這裡進一步處理「系統開始變大後，事件與狀態如何不失控」。

## 章節列表

| 章節                         | 主題                         | 關鍵收穫                                                        |
| ---------------------------- | ---------------------------- | --------------------------------------------------------------- |
| [4.1](component-boundaries/) | 事件來源、處理流程與狀態邊界 | 用邊界拆開 reader、normalizer、processor、repository、publisher |
| [4.2](dedup-key/)            | 事件去重與語義鍵設計         | 用 domain key、時間窗口與清理策略管理重複事件                   |
| [4.3](source-of-truth/)      | [Source of Truth](../../backend/knowledge-cards/source-of-truth)：狀態邊界    | 集中狀態轉移、保護可變資料、設計 [projection](../../backend/knowledge-cards/projection)                     |
| [4.4](event-fusion/)         | 多來源 event 融合            | 把 HTTP、[queue](../../backend/knowledge-cards/queue)、timer 等來源收斂到同一套 domain event 流程      |

## 本模組使用的範例主題

本模組使用虛構的通知與工作處理服務作為範例。服務可能從 HTTP callback、queue message、timer 或檔案 reader 收到事件，最後更新內部狀態並推送通知。

範例只用來展示 Go 的設計方法，不假設讀者正在維護任何特定專案。

## 本模組的 Go 核心概念

- 用 struct 定義穩定的內部事件模型。
- 用 interface 表達 reader、repository、publisher 這類能力。
- 用 context 傳遞 request lifecycle、取消與逾時。
- 用 mutex 或單一 goroutine 保護共享狀態。
- 用 package 邊界限制 adapter、application、domain 的依賴方向。
- 用 table-driven test 驗證 normalize、dedup 與狀態轉移。

## 學習重點

學完本模組後，你應該能判斷：

1. 外部訊號是否應該轉成 domain event
2. 去重應該使用哪些欄位，哪些欄位不應進入 key
3. 狀態真相應該由哪個元件擁有
4. 新事件來源應該新增 adapter，還是修改 processor
5. ports/adapters 與 event-driven service 如何在 Go 中自然結合

## 章節粒度說明

本模組的四章分別處理事件系統的四個核心面向，不建議硬拆成更小的孤立段落。事件來源、去重、狀態真相與多來源融合會互相影響；拆得太碎會讓讀者看不到一筆事件如何從外部輸入走到狀態更新與推送。

閱讀時可以把四章視為一條路線：

1. [事件來源、處理流程與狀態邊界](component-boundaries/)：先建立元件分工。
2. [事件去重與語義鍵設計](dedup-key/)：再定義「同一事件」的語意。
3. [Source of Truth：狀態邊界](source-of-truth/)：接著決定誰能改狀態。
4. [多來源 event 融合](event-fusion/)：最後處理 HTTP、queue、timer 等多入口協作。

## 本模組不處理

本模組不實作完整 message queue、分散式 [transaction](../../backend/knowledge-cards/transaction) 或 event sourcing 平台。這些主題需要更多基礎設施與操作細節；本模組先聚焦 Go 程式內部如何建立清楚的事件與狀態邊界。後續可接 [資料庫 transaction 與 schema migration](../07-distributed-operations/database-transactions/) 以及 [Durable queue、outbox 與 idempotency](../07-distributed-operations/outbox-idempotency/)。

## 學習時間

預計 3-4 小時
