---
title: "Request Unit"
date: 2026-05-27
description: "Cosmos DB 的容量抽象單位、1 RU = 1KB document strong-consistent read 的 CPU + memory + IOPS 綜合 cost、寫 ~5 RU、複雜 query 數百 RU"
weight: 365
---

Request Unit（RU）的核心概念是「Cosmos DB 把 CPU + memory + IOPS 等資源綜合成單一抽象計量、1 RU 對應 1KB document 的 strong-consistent read 成本」。它的責任是把容量規劃從「估 CPU / IOPS / working set」改成「估每個操作多少 RU × 操作頻率」、讓 throttle / scaling / 計費都用同一個量綱。可先對照 [Cost Per Request](/backend/knowledge-cards/cost-per-request/)。

## 概念位置

RU 出現在 Cosmos DB 全產品線、跟 [Cost Per Request](/backend/knowledge-cards/cost-per-request/) 是抽象與具體實作的對應 — cost-per-request 是通用概念、RU 是 Cosmos DB 把它落地成單一可計量單位。跟 [Throughput](/backend/knowledge-cards/throughput/) 區分：後者是 raw 計量（每秒幾筆 / 幾 MB）、RU 是 vendor 抽象、不可直接互換。跟 [Workload Model](/backend/knowledge-cards/workload-model/) 互補 — workload model 決定 access pattern、access pattern 決定 RU consumption、兩者一起才能估容量。

## 可觀察訊號與例子

需要 RU 判讀的訊號是「Cosmos DB throttle 在 monthly bill 之前就先出現、team 估容量發現估不出來」。[9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) 揭露對照：1 RU = 1KB strong-consistent read、寫 ~5 RU、複雜 query 數百 RU；100 萬 RU/s 壓測通過（壓測數字、非 production 持續、case 自己警示）。[9.C21 ASOS Cosmos DB](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 跟 [9.C30 Microsoft 365 Cosmos DB](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 揭露 Black Friday 10x 流量下 autoscale 跟不上 throttle、index policy 改動讓 write RU 漲 30%。

## 設計責任

設計時要把 RU 估算當 *工程動作*、不是 vendor 廣告數字 — 量單一 query 的 `x-ms-request-charge` header、不是看 slow query log；改 index policy 影響 RU、但不改 query 速度、改的是 cost。team 從 CPU + IOPS 思維轉到 RU 思維通常需要 4-6 週、selection 評估時不能只比 monthly bill 就做 ROI 結論、思維遷移成本可能高過 vendor 廣告價差。autoscale 跟 provisioned 的選擇要看 burst 形狀跟 hot partition 風險、壓測通過數字不能直接當 production sizing 上界。
