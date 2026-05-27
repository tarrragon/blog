---
title: "Hybrid Logical Clock"
date: 2026-05-27
description: "用 physical wall clock + monotonic logical counter 給每個事件 timestamp、靠軟體 max-offset 保證跨節點時鐘差不超過上限、超過 panic 保護一致性"
weight: 363
---

Hybrid Logical Clock（HLC）的核心概念是「給每個事件一個 `(physical, logical)` timestamp、physical 來自 NTP 同步的 wall clock、logical 是單調遞增的 counter 處理同一 physical tick 內的事件順序」。它的責任是讓跨節點 event ordering 可以用軟體保證、不需要 GPS + 原子鐘等專用硬體、代價是要承擔 max-offset 邊界內的不確定性。可先對照 [TrueTime](/backend/knowledge-cards/truetime/)。

## 概念位置

HLC 出現在 CockroachDB 等不依賴專用硬體的 distributed SQL、跟 [TrueTime](/backend/knowledge-cards/truetime/) 是對照關係 — 兩者解同一個 event ordering 問題、HLC 用軟體 + NTP、TrueTime 用 GPS + 原子鐘。跟 [External Consistency](/backend/knowledge-cards/external-consistency/) 互補但不等同：HLC 保證 linearizability、不保證 external consistency；TrueTime 加 commit-wait 才能達 external consistency。跟 [Linearizability](/backend/knowledge-cards/linearizability/) 緊密相關 — HLC 在 max-offset 契約成立的前提下、cluster 內所有 transaction 仍是 linearizable。

## 可觀察訊號與例子

需要 HLC 判讀的訊號是「distributed SQL cluster 節點 NTP 異常、寫入路徑開始 panic」。[9.C39 DoorDash CockroachDB](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) 跟 [9.C40 Netflix CockroachDB](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 都用 HLC 撐線性化、NTP 是 ops first-class concern。CockroachDB 預設 `max-offset` 是 500ms、節點時鐘飄超過就自動 panic、不會發出錯誤 commit；HLC 在跨 node RPC 時把 logical counter 同步推進、確保事件因果順序在跨節點仍可推導。

## 設計責任

選擇 HLC 路徑就要把 NTP / chronyd 維運當成 production-critical — 不是「裝了就好」、要監控時鐘漂移、設 alert 在 max-offset 的一半左右觸發。max-offset 配置過寬（例如改 5s 想避免 panic）會在跨節點交易順序判讀上引入錯誤、不是 ops 「彈性」、是把線性化保證打破。對比 TrueTime 路徑、HLC 不需要付 commit-wait latency tax、但 cross-cloud / on-prem 部署彈性是它的主要 trade-off 動機、不要為了「不付 commit-wait」就選 HLC、要為了部署環境選 HLC、commit-wait 不付只是順帶結果。
