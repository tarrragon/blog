---
title: "Distributed SQL"
date: 2026-05-13
description: "把 SQL 與交易語意延伸到多節點與多區域的資料庫形態"
weight: 242
---

Distributed SQL 的核心概念是「保留 SQL 與交易語意，同時把資料與計算分散到多節點」。它承擔的是一致性、擴展性與故障收斂的協調成本，並常作為 [global-oltp](/backend/knowledge-cards/global-oltp/) 的資料層基礎。

## 概念位置

Distributed SQL 介於單區域 relational database 與最終一致的 key-value 之間。它通常使用 consensus 協議、分區與複寫，來支撐 [global-oltp](/backend/knowledge-cards/global-oltp/) 或高可用 OLTP。可對照 [database](/backend/knowledge-cards/database/) 與 [partition](/backend/knowledge-cards/partition/)。

## 可觀察訊號與例子

需要 distributed SQL 的訊號是「單機或單主架構已成長瓶頸，且業務仍要求交易一致性」。常見例子是跨區帳務、全球訂單、強一致庫存。若業務主要追求吞吐且可接受不一致，NoSQL 或事件流設計通常更划算。

## 設計責任

選 distributed SQL 要明確評估三項代價：跨節點協調延遲、容量預留、運維複雜度。若只看峰值吞吐而忽略協調成本，會在故障與擴容時暴露結構性風險。
