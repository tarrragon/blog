---
title: "Single Writer Model"
date: 2026-05-22
description: "說明單寫者模型如何序列化寫入，並成為系統的容量邊界"
weight: 329
---

Single Writer Model 的核心概念是同一個邏輯資料庫在任一時間只允許一條 writer path，所有寫入被序列化。它讓寫入路徑簡單、省去分散式寫入協調，代價是寫入吞吐有明確上限。它是 SQLite WAL mode 與許多 leader-based 系統的並發模型，和 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)、[Embedded Database](/backend/knowledge-cards/embedded-database/) 一起決定寫入行為。

## 跟其他概念的關係

Single Writer Model 位在並發模型的一端 — 寫入併發度上限為一。它和「多 reader 並行」可以共存：SQLite WAL mode 允許多個 reader 與一個 writer 同時運作。要擴展寫入時，靠的是改變架構（例如分區、分庫或換成 [Distributed SQL](/backend/knowledge-cards/distributed-sql/)），增加 writer 在此模型下行不通。

## 可觀察訊號與例子

single writer 仍夠用的訊號是寫入可以用一個 writer 排隊完成、busy 或 lock timeout 偶發且短。需要重新設計的訊號是寫入長期排隊、busy timeout 從偶發變成常態。常見誤判是把 busy timeout 調大當成擴容 — 那只是讓請求等更久；也常見多個 instance 同時寫同一個檔案，破壞 single writer 假設。

## 判斷條件與後果

Single Writer Model 的前提是系統裡只有一個 writer，前提被破壞與寫入量達到上限是兩種不同的狀態。多個 instance 同時寫同一個資料庫檔案時，single writer 假設被破壞，寫入彼此爭搶 lock，busy 錯誤增加；所以 writer 是誰要明確指認並集中，LiteFS 類方案用 primary lease 決定誰持有 writer 角色，應用層把寫入路徑收斂到單一節點或單一序列化點。寫入量超過單一 writer 的吞吐時，請求在佇列裡排隊，busy timeout 從偶發變成常態，這時調大 busy timeout 只讓請求等更久，吞吐上限不變。單一 writer 的吞吐是這個模型的硬上限，增加 writer 在此模型下行不通，容量規劃以它為上限計算，需求超過時改的是架構：分區或 [Distributed SQL](/backend/knowledge-cards/distributed-sql/)。
