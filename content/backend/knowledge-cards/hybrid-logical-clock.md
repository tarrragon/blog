---
title: "Hybrid Logical Clock"
date: 2026-05-27
description: "用 physical wall clock + monotonic logical counter 給每個事件 timestamp、靠軟體 max-offset 保證跨節點時鐘差不超過上限、超過 panic 保護一致性"
weight: 364
---

Hybrid Logical Clock（HLC）的核心概念是「給每個事件一個 `(physical, logical)` timestamp、physical 來自 NTP 同步的 wall clock、logical 是單調遞增的 counter 處理同一 physical tick 內的事件順序」。它的責任是讓跨節點 event ordering 可以用軟體保證、不需要 GPS + 原子鐘等專用硬體、代價是要承擔 max-offset 邊界內的不確定性。可先對照 [TrueTime](/backend/knowledge-cards/truetime/)。

## 跟其他概念的關係

HLC 出現在 CockroachDB 等不依賴專用硬體的 distributed SQL、跟 [TrueTime](/backend/knowledge-cards/truetime/) 是對照關係 — 兩者解同一個 event ordering 問題、HLC 用軟體 + NTP、TrueTime 用 GPS + 原子鐘。跟 [External Consistency](/backend/knowledge-cards/external-consistency/) 互補但不等同：HLC 保證 linearizability、不保證 external consistency；TrueTime 加 commit-wait 才能達 external consistency。跟 [Linearizability](/backend/knowledge-cards/linearizability/) 緊密相關 — HLC 在 max-offset 契約成立的前提下、cluster 內所有 transaction 仍是 linearizable。

## 可觀察訊號與例子

需要 HLC 判讀的訊號是「distributed SQL cluster 節點 NTP 異常、寫入路徑開始 panic」。[DoorDash CockroachDB](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) 跟 [Netflix CockroachDB](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 都用 HLC 撐線性化、NTP 是 ops first-class concern。CockroachDB 預設 `max-offset` 是 500ms、節點時鐘飄超過就自動 panic、不會發出錯誤 commit；HLC 在跨 node RPC 時把 logical counter 同步推進、確保事件因果順序在跨節點仍可推導。

## 判斷條件與後果

HLC 的正確性以節點時鐘偏差保持在 max-offset 之內為前提，所以 NTP 或 chronyd 的時鐘同步是 production-critical 的依賴。節點時鐘飄超過 max-offset 時，CockroachDB 讓那個節點 panic，寫入路徑中斷，代價是可用性，換到的是不發出順序錯誤的 commit；時鐘漂移有監控，alert 設在 max-offset 的一半左右觸發時，漂移在造成 panic 之前就被看到。max-offset 調寬時（例如為了避免 panic 改成 5s），panic 變少，代價是新上限之內的時鐘偏差都被當成可接受，跨節點交易的順序判讀可能出錯，線性化保證不再成立。HLC 與 [TrueTime](/backend/knowledge-cards/truetime/) 之間的選擇依部署環境：cross-cloud 或 on-prem 部署拿不到 GPS 與原子鐘時，HLC 是可行的路徑，省下 commit-wait 的延遲是這個選擇的附帶結果，單為了省下 commit-wait 而選 HLC，換來的是上面那份時鐘維運的依賴。
