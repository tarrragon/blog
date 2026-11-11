---
title: "Replication Slot"
date: 2026-05-22
description: "說明邏輯複製如何用 slot 追蹤消費進度，並對來源端造成保留壓力"
weight: 327
---

Replication Slot 的核心概念是來源資料庫為每個下游 consumer 保留的進度標記 — 它記錄 consumer 確認到哪個位置，並據此保留尚未被消費的 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)。slot 讓 consumer 斷線後仍能從正確位置續傳，代價是 consumer 停擺時 log 會在來源端持續累積。它是 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 與邏輯複製的進度基礎，和 messaging 的 [Offset](/backend/knowledge-cards/offset/) 相鄰但責任不同。

## 跟其他概念的關係

Replication Slot 位在來源資料庫與下游 consumer 之間，是一個有狀態的 production resource。它和 [Offset](/backend/knowledge-cards/offset/) 都是消費進度，差別在反壓方向：offset 落後不會壓垮 producer，slot 落後會讓來源端為了保留 WAL 而吃光磁碟。PostgreSQL 的 replication slot 是典型例子，[Consumer Lag](/backend/knowledge-cards/consumer-lag/) 是它對應的健康指標。

## 可觀察訊號與例子

需要監控 slot 的訊號是來源資料庫磁碟用量上升、但寫入量沒有等比增加。常見原因是 Debezium connector 或 replica 離線，slot 仍在保留 WAL。一個 inactive slot 在高寫入服務上可以在數小時內撐爆 primary 磁碟，屬於高優先事故訊號。

## 判斷條件與後果

Slot 的判斷對象是每個 slot 背後的 consumer 是否還在推進 confirmed 位置。consumer 推進時，來源端只保留它還沒確認的 WAL；consumer 離線或永久退場而 slot 還在時，來源端持續保留 WAL，磁碟用量上升到寫滿 primary，原因是 slot 在 consumer 確認之前不讓 WAL 被回收。這個代價跟 offset 的方向相反，由來源資料庫承擔，所以 slot 數量與保留量屬於來源端容量規劃的一部分。retained WAL 大小與 inactive 狀態沒有告警時，這個累積要等磁碟告警才被看到，高寫入服務上那時離寫滿可能只剩數小時。consumer 退場之後由誰 drop slot 沒有指定時，slot 會一直留著，所以 slot 建立時就指定這個 owner。
