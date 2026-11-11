---
title: "Request Unit"
date: 2026-05-27
description: "Cosmos DB 的容量抽象單位、1 RU = 1KB document strong-consistent read 的 CPU + memory + IOPS 綜合 cost、寫 ~5 RU、複雜 query 數百 RU"
weight: 366
---

Request Unit（RU）的核心概念是「Cosmos DB 把 CPU + memory + IOPS 等資源綜合成單一抽象計量、1 RU 對應 1KB document 的 strong-consistent read 成本」。它的責任是把容量規劃從「估 CPU / IOPS / working set」改成「估每個操作多少 RU × 操作頻率」、讓 throttle / scaling / 計費都用同一個量綱。可先對照 [Cost Per Request](/backend/knowledge-cards/cost-per-request/)。

## 跟其他概念的關係

RU 出現在 Cosmos DB 全產品線、跟 [Cost Per Request](/backend/knowledge-cards/cost-per-request/) 是抽象與具體實作的對應 — cost-per-request 是通用概念、RU 是 Cosmos DB 把它落地成單一可計量單位。跟 [Throughput](/backend/knowledge-cards/throughput/) 區分：後者是 raw 計量（每秒幾筆 / 幾 MB）、RU 是 vendor 抽象、不可直接互換。跟 [Workload Model](/backend/knowledge-cards/workload-model/) 互補 — workload model 決定 access pattern、access pattern 決定 RU consumption、兩者一起才能估容量。

## 可觀察訊號與例子

需要 RU 判讀的訊號是「Cosmos DB throttle 在 monthly bill 之前就先出現、team 估容量發現估不出來」。[Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) 揭露對照：1 RU = 1KB strong-consistent read、寫 ~5 RU、複雜 query 數百 RU；100 萬 RU/s 壓測通過（壓測數字、非 production 持續、case 自己警示）。[ASOS Cosmos DB](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 跟 [Microsoft 365 Cosmos DB](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 揭露 Black Friday 10x 流量下 autoscale 跟不上 throttle、index policy 改動讓 write RU 漲 30%。

## 判斷條件與後果

RU 估算的判斷對象是每個操作實際消耗多少 RU。估算來源是 vendor 的對照數字或 slow query log 時，估出來的值跟實際計費與 throttle 對不上，原因是 RU 隨 document 大小與 index policy 改變，而 slow query log 記的是速度；每個 response 的 `x-ms-request-charge` header 回報這次操作實際的 RU，從它量才對得上。index policy 的改動屬於同一類：它改的是每次寫入的 RU，query 速度可能不變，所以只看延遲的回歸測試抓不到成本上升。團隊從 CPU 與 IOPS 的估法轉到 RU 的估法通常需要 4 到 6 週，選型時只比 monthly bill 而沒算這段遷移成本，ROI 結論會高估，這段成本可能高過 vendor 之間的價差。burst 比 autoscale 擴容快、或流量集中在少數 hot partition 時，總量還沒到上限就先被 throttle，所以 autoscale 與 provisioned 依 burst 形狀與 hot partition 風險選，壓測通過的數字也不直接當成 production sizing 的上界。
