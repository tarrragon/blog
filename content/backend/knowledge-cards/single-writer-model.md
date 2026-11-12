---
title: "Single Writer Model"
date: 2026-05-22
description: "說明單寫者模型如何序列化寫入，並成為系統的容量邊界"
weight: 329
tags: ["backend", "database", "sqlite", "concurrency", "knowledge-card"]
---

Single Writer Model 的核心概念是同一個邏輯資料庫在任一時間只允許一條 writer path，所有寫入被序列化。它讓寫入路徑簡單、省去分散式寫入協調，代價是寫入吞吐有明確上限。它是 SQLite WAL mode 與許多 leader-based 系統的並發模型，和 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)、[Embedded Database](/backend/knowledge-cards/embedded-database/) 一起決定寫入行為。

## 跟其他概念的關係

Single Writer Model 位在並發模型的一端 — 寫入併發度上限為一。它和「多 reader 並行」可以共存：SQLite WAL mode 允許多個 reader 與一個 writer 同時運作。要擴展寫入時，靠的是改變架構（例如分區、分庫或換成 [Distributed SQL](/backend/knowledge-cards/distributed-sql/)），增加 writer 在此模型下行不通。

## 可觀察訊號與例子

single writer 仍夠用的訊號是寫入可以用一個 writer 排隊完成、busy 或 lock timeout 偶發且短。需要重新設計的訊號是寫入長期排隊、busy timeout 從偶發變成常態。常見誤判是把 busy timeout 調大當成擴容 — 那只是讓請求等更久。等待時間接近 0 就回 busy 的錯誤，成因多半是交易先讀後寫（[Check-then-act（先讀後寫）](/backend/knowledge-cards/check-then-act/)），跟吞吐量無關。

## 判斷條件與後果

Single Writer Model 的前提是系統裡只有一個 writer，前提被破壞與寫入量達到上限是兩種不同的狀態。多個寫入者分兩種情形。同一台機器、本地磁碟上的幾個程序寫同一個檔案時，寫入鎖在程序之間照樣有效，寫入仍然一個接一個執行，前提沒有被破壞，代價是程序之間爭搶這把鎖、busy 錯誤增加。跨機器共用一個檔案、或檔案放在網路檔案系統上時，鎖的語意不可靠，兩個寫入者可能同時寫，single writer 假設被破壞，後果是資料損毀；所以 writer 是誰要明確指認並集中，LiteFS 類方案用 primary lease 決定誰持有 writer 角色，應用層把寫入路徑收斂到單一節點或單一序列化點。寫入量超過單一 writer 的吞吐時，請求在佇列裡排隊，busy timeout 從偶發變成常態，這時調大 busy timeout 只讓請求等更久，吞吐上限不變。單一 writer 的吞吐是這個模型的硬上限，增加 writer 在此模型下行不通，容量規劃以它為上限計算，需求超過時改的是架構：分區、[Distributed SQL](/backend/knowledge-cards/distributed-sql/)，或換成 PostgreSQL 這類讓多個寫入者並行的伺服器。換成多寫入者之後，原本靠單一寫入者排隊而正確的先讀後寫會在並行時寫出[遺失更新](/backend/knowledge-cards/lost-update/)或寫入偏斜，要改寫成約束、列鎖或隔離等級，兩種形態的實測在 [SQL.20 引擎的部署形態與 SQL 構造](/backend/01-database/sql/deployment-shape-and-sql-constructs/)。
