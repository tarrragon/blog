---
title: "Event Sourcing"
date: 2026-06-22
description: "說明用 append-only 事件流取代 mutable state 作為正式紀錄的設計模式、需求判準與代價"
weight: 329
tags: ["backend", "architecture", "database"]
---

Event sourcing 的核心概念是「不存 current state、存產生 current state 的所有事件」。儲存層是 [event log](/backend/knowledge-cards/event-log/)，讀取面透過 [projection](/backend/knowledge-cards/projection/) 推算 current state。每一次狀態變更被記錄為一筆不可變的事件（event），current state 透過重播（replay）事件序列推算出來。正式紀錄是事件流本身，current state 是派生物。

## 概念位置

Event sourcing 是一種資料持久化策略，改變的是「狀態怎麼被記錄」而非「狀態怎麼被讀取」。它跟 [CQRS](/backend/knowledge-cards/cqrs/) 經常搭配但概念獨立 — event sourcing 處理寫入模型（append-only event log 取代 mutable row），CQRS 處理讀寫分離。可以有 event sourcing 但沒有 CQRS（讀寫都直接操作 event store），也可以有 CQRS 但沒有 event sourcing（寫入仍用 CRUD）。

Event sourcing 的儲存層是 [event log](/backend/knowledge-cards/event-log/)。讀取面透過 [projection](/backend/knowledge-cards/projection/) 把事件流轉換成查詢用的 [read model](/backend/knowledge-cards/read-model/)。

## 設計判準

Event sourcing 的設計價值來自「需要完整變更歷史」的業務需求。判準是：業務是否需要回答「某個時間點的狀態是什麼」或「狀態怎麼從 A 變成 B」。

**適合的場景**：

- 金融帳務 — 餘額的每一筆增減都是 audit 事件，法規要求能追溯任意時點的 balance
- 訂單流程 — 每個狀態轉換（建立→付款→出貨→完成）是 business event，需要重建任意階段
- 法規合規 — 完整變更歷史是合規證據，刪除或覆寫正式紀錄違反要求
- 需要 replay 能力 — downstream consumer 落後或資料損壞時，能從 event log 重建

**不適合的場景**：

- 簡單 CRUD — 狀態覆寫即可、不需要歷史、event sourcing 的 overhead 遠大於收益
- 需要直接查 current state 的高頻場景 — 每次讀取都 replay 整條事件流延遲太高，必須搭配 projection 維護 snapshot，增加系統複雜度
- 事件 schema 變更頻繁 — 舊事件需要被新版 schema 正確 replay，schema evolution 成本高

## 代價

**讀取複雜度**：current state 不再是一筆 row，而是需要 replay 或 projection 推算。讀取路徑的設計從「查一筆 record」變成「維護多個 [read model](/backend/knowledge-cards/read-model/) + 保證 projection 正確性 + 處理 projection lag」。

**事件 schema evolution**：事件一旦寫入就不可變，但業務需求會改變事件結構。版本化 event schema（upcasting）是長期維護的核心挑戰 — 新版 projection 要能正確消費舊版事件。

**儲存成長**：事件永不刪除（或只做 retention），儲存量隨時間持續成長。高頻寫入的系統可能需要 snapshot 機制（定期存一份 current state 快照，replay 從 snapshot 開始而非從頭）來控制 replay 時間。

**除錯難度**：bug 可能是某個 event handler 在 replay 時產生錯誤結果。除錯需要重現特定事件序列的 replay，比查一筆 mutable record 的 diff 更複雜。

## 跟其他概念的關係

- [Event log](/backend/knowledge-cards/event-log/) — event sourcing 的儲存層，append-only 的事件序列
- [Projection](/backend/knowledge-cards/projection/) — 把 event log 轉換成可查詢的 read model 的機制
- [Read model](/backend/knowledge-cards/read-model/) — projection 的輸出，為特定查詢需求最佳化的資料形狀
- [CQRS](/backend/knowledge-cards/cqrs/) — 讀寫分離的設計框架，event sourcing 是其中一種 write model 實作
- [Saga](/backend/knowledge-cards/saga/) — 跨服務的分散事務，event sourcing 提供每個 step 的事件紀錄
