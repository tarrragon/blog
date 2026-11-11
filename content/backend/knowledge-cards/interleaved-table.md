---
title: "Interleaved Table"
date: 2026-05-27
description: "Spanner 把 parent / child table row 物理交錯儲存、parent + child JOIN 不跨 split"
weight: 370
---

Interleaved table 的核心概念是「parent table 跟 child table 的 row 在 storage layer 物理交錯儲存 — child row 跟對應 parent row 落在同一個 split」。它把「foreign key 是 logical constraint」翻成「parent-child access 是 physical co-location」、跟 [Range Sharding](/backend/knowledge-cards/range-sharding/) 是相鄰機制（前者是 row-level co-location、後者是 key-space transparent split）、跟 PostgreSQL declarative 的 [Table Partitioning](/backend/knowledge-cards/table-partitioning/) 不同層（後者是單機表結構、interleaved 是分散式 SQL 跨 Paxos group 的 row co-location）。

## 跟其他概念的關係

Spanner 是 interleaved table 的代表 vendor — `CREATE TABLE Order ... INTERLEAVE IN PARENT Customer ON DELETE CASCADE` 把 child row 物理黏到 parent row 旁邊。Storage layout 從 `[c1, c2, c3, ...] [o1, o2, o3, ...]` 變成 `[c1, c1.o1, c1.o2, c2, c2.o1, c2.o2, c3, ...]` — parent + child JOIN 在同一個 split 完成、不跨 Paxos group、commit wait + Paxos round-trip 只算一份。CockroachDB 的 `REGIONAL BY ROW` + parent-child placement 是相鄰概念（透過 region locality 達成類似 co-location 效果、但機制不同）。

跟 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 共軸 — interleaved 讓 transaction boundary 跟 storage boundary對齊、跨 split transaction 大幅減少。

## 可觀察訊號與例子

適合 interleaved table 的訊號是「access pattern 固定 parent → child、JOIN 頻率高、跨 split JOIN p99 latency 撐不住」。典型情境：customer → orders、user → posts、tenant → records 這類 1:N 強耦合資料。Spanner 文件揭露的硬限要記住：child PK 必須以 parent PK 為 prefix、最深 7 層、`ON DELETE` 只能 CASCADE 或 NO ACTION（不像 PG FK 有 SET NULL / SET DEFAULT）、一旦建立無法 ALTER 改 interleave — 要改就是 export + recreate + import、不是 ALTER。

## 判斷條件與後果

Interleave 的關係建立之後無法用 ALTER 改，要改得 export、重建再 import，資料量小時這個代價低，到 10 億 row 時是一項大工程，所以哪些 parent-child 要 interleave 在 schema 設計階段就依 access pattern 決定。child PK 必須以 parent PK 為 prefix，這個限制讓「child 跟誰 co-locate」成為 schema 的主軸，logical 關聯只是其中一個考量。三種情境下 interleave 換到的是代價：child 對多個 parent 有 N:M 關係時，child 只能存放在其中一個 parent 旁邊，對其他 parent 的 JOIN 照樣跨 split；access pattern 是跨 parent 的 aggregation（報表跨所有 customer 算 orders 總和）時，掃描本來就要走過全部 parent，co-location 省不到跨 split 的成本；parent 寫入頻繁而 child 很少寫時，parent 所在的 hot range 同時涵蓋它的 child，child 跟著承受那個 range 的負載與 split。後一種情形把 parent 的 hot range 擴散到 child，延遲比 child 獨立成表時更差。
