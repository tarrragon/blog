---
title: "GTID"
date: 2026-05-22
description: "說明全域交易識別碼如何讓複製進度與故障切換不依賴實體 log 位置"
weight: 348
---

GTID（Global Transaction Identifier）的核心概念是給每一筆交易一個全域唯一的識別碼，讓複製進度用「套用到哪個交易」來表示，而不是用某台機器上的實體 log 檔名與位移。它讓 replica 重接、故障切換與拓撲調整不必手算 log 位置。它是 [Replication Channel](/backend/knowledge-cards/replication-channel/) 與 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 追蹤位置的基礎。

## 概念位置

GTID 位在複製拓撲的進度標記層。沒有 GTID 時，replica 的進度是「primary 的 binlog 檔加位移」，這個座標換一台 primary 就失效；GTID 用交易本身的識別碼當座標，跨機器仍成立。它讓 [Failover](/backend/knowledge-cards/failover/) 後 replica 能自動找到接續點，也讓 [Replication Lag](/backend/knowledge-cards/replication-lag/) 可以用「落後幾個交易」表達。

## 可觀察訊號與例子

需要 GTID 的訊號是拓撲會變動：會做故障切換、會加減 replica、會調整複製鏈。用實體 log 位置時，每次換 primary 都要手動換算每個 replica 的接續點，容易出錯；GTID 讓 replica 指向新 primary 後自動續傳。CDC 工具也常用 GTID 當位置標記，讓 consumer 斷線重連後既不漏事件也不重複。

## 設計責任

設計時要在拓撲全體一致地啟用 GTID，並讓故障切換、CDC consumer 與備援流程都以 GTID 為位置基準。要監控每個 replica 與 consumer 已套用的 GTID 集合，據此判斷延遲與缺口。observability 要能看到 GTID 落後量與是否有 gap。
