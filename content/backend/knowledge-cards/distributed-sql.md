---
title: "Distributed SQL"
date: 2026-05-13
description: "把 SQL 與交易語意延伸到多節點與多區域的資料庫形態"
weight: 243
---

Distributed SQL 的核心概念是「保留 SQL 與交易語意，同時把資料與計算分散到多節點」。它承擔的是一致性、擴展性與故障收斂的協調成本，並常作為 [global-oltp](/backend/knowledge-cards/global-oltp/) 的資料層基礎。

## 跟其他概念的關係

Distributed SQL 介於單區域 relational database 與最終一致的 key-value 之間。它通常使用 consensus 協議、分區與複寫，來支撐 [global-oltp](/backend/knowledge-cards/global-oltp/) 或高可用 OLTP。可對照 [database](/backend/knowledge-cards/database/) 與 [partition](/backend/knowledge-cards/partition/)。

## 可觀察訊號與例子

需要 distributed SQL 的訊號是「單機或單主架構已成長瓶頸，且業務仍要求交易一致性」。常見例子是跨區帳務、全球訂單、強一致庫存。若業務主要追求吞吐且可接受不一致，NoSQL 或事件流設計通常更划算。

## 判斷條件與後果

Distributed SQL 的跨節點協調延遲、容量預留與運維複雜度三項代價，在正常負載下的峰值吞吐測試裡看不到。每一筆寫入都經過 consensus 複寫，多數副本確認之後才提交，所以寫入延遲高於單機資料庫；節點故障或擴容時，分區與 leader 要重新分配，協調工作集中在這段時間，預留的容量不夠時表現為延遲升高或交易逾時。只用峰值吞吐評估時，故障與擴容這兩個情境不在評估範圍裡，容量與運維上的缺口要到事件發生的當下才出現。業務主要追求吞吐、可以接受不一致時，付出這三項代價換到的交易一致性用不上，NoSQL 或事件流設計的總成本較低。
