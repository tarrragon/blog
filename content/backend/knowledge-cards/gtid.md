---
title: "GTID"
date: 2026-05-22
description: "說明全域交易識別碼如何讓複製進度與故障切換不依賴實體 log 位置"
weight: 349
---

GTID（Global Transaction Identifier）的核心概念是給每一筆交易一個全域唯一的識別碼，讓複製進度用「套用到哪個交易」來表示，而不是用某台機器上的實體 log 檔名與位移。它讓 replica 重接、故障切換與拓撲調整不必手算 log 位置。它是 [Replication Channel](/backend/knowledge-cards/replication-channel/) 與 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 追蹤位置的基礎。

## 跟其他概念的關係

GTID 位在複製拓撲的進度標記層。沒有 GTID 時，replica 的進度是「primary 的 binlog 檔加位移」，這個座標換一台 primary 就失效；GTID 用交易本身的識別碼當座標，跨機器仍成立。它讓 [Failover](/backend/knowledge-cards/failover/) 後 replica 能自動找到接續點，也讓 [Replication Lag](/backend/knowledge-cards/replication-lag/) 可以用「落後幾個交易」表達。

## 可觀察訊號與例子

需要 GTID 的訊號是拓撲會變動：會做故障切換、會加減 replica、會調整複製鏈。用實體 log 位置時，每次換 primary 都要手動換算每個 replica 的接續點，容易出錯；GTID 讓 replica 指向新 primary 後自動續傳。CDC 工具也常用 GTID 當位置標記，讓 consumer 斷線重連後既不漏事件也不重複。

## 判斷條件與後果

GTID 的判斷條件是拓撲裡記錄複製位置的元件是否都用同一種位置基準。部分節點啟用 GTID、部分仍記 binlog 檔加位移時，故障切換後那些節點的接續點仍要手算，自動續傳只在啟用 GTID 的節點上成立；CDC consumer 或備援流程仍記實體 log 位置時，換一台 primary 之後那個位置失效，consumer 重連時可能漏事件或重複。每個 replica 與 consumer 已套用的 GTID 集合有監控時，延遲用落後幾個交易表達，集合裡出現的 gap 代表有交易沒有套用，原因是集合記錄的是交易識別碼本身，缺了哪一筆在集合裡看得出來。
