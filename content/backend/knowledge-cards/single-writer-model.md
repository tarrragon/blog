---
title: "Single Writer Model"
date: 2026-05-22
description: "說明單寫者模型如何序列化寫入，並成為系統的容量邊界"
weight: 328
---

Single Writer Model 的核心概念是同一個邏輯資料庫在任一時間只允許一條 writer path，所有寫入被序列化。它讓寫入路徑簡單、省去分散式寫入協調，代價是寫入吞吐有明確上限。它是 SQLite WAL mode 與許多 leader-based 系統的並發模型，和 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)、[Embedded Database](/backend/knowledge-cards/embedded-database/) 一起決定寫入行為。

## 概念位置

Single Writer Model 位在並發模型的一端 — 寫入併發度上限為一。它和「多 reader 並行」可以共存：SQLite WAL mode 允許多個 reader 與一個 writer 同時運作。要擴展寫入時，靠的不是增加 writer，而是改變架構，例如分區、分庫或換成 [Distributed SQL](/backend/knowledge-cards/distributed-sql/)。

## 可觀察訊號與例子

single writer 仍夠用的訊號是寫入可以用一個 writer 排隊完成、busy 或 lock timeout 偶發且短。需要重新設計的訊號是寫入長期排隊、busy timeout 從偶發變成常態。常見誤判是把 busy timeout 調大當成擴容 — 那只是讓請求等更久；也常見多個 instance 同時寫同一個檔案，破壞 single writer 假設。

## 設計責任

設計時要明確指認「誰是 writer」並確保系統真的只有一個。LiteFS 類方案用 primary lease 把 writer 角色集中；應用層要把寫入路徑收斂到單一節點或單一序列化點。容量規劃要把單 writer 吞吐當作硬上限，超過時改走分區或 [Distributed SQL](/backend/knowledge-cards/distributed-sql/)，而不是疊加 writer。
