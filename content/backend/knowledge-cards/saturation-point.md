---
title: "Saturation Point"
date: 2026-05-12
description: "說明系統從線性穩態進入 latency 指數成長區的關鍵流量點"
weight: 223
---

Saturation point 的核心概念是「系統 latency 從線性穩態進入指數成長的流量臨界點」。容量曲線分三段：linear → knee → cliff。knee point 是設計容量上限（safe operating zone 的邊界）、cliff 是延遲失控、吞吐量開始下降的區段；進入 cliff 之後服務呈現哪一種結果（請求失敗、無回應、程序終止），見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)。可先對照 [Load Test](/backend/knowledge-cards/load-test/)。

## 跟其他概念的關係

Saturation 指進入 latency 不可預測區：程序仍在、請求仍在完成，與程序終止是不同的狀態。健康系統運轉在 knee point 以下 50-70%。M/M/c queueing theory 顯示：utilization 接近 80% 時、queue length 跟 latency 指數成長 — 這個 80% 就是常見的 knee。可先對照 [Little's Law](/backend/knowledge-cards/little-law/)。

## 可觀察訊號與例子

Saturation point 出現的訊號是「pressure 增加 10%、latency 增加 100%」。對應案例：[Tixcraft DynamoDB IOPS 從 20 衝到 135K](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — partition 設計均勻時 saturation point 推到極遠；hot partition 場景下 saturation point 提前出現、即使整體 capacity 還有餘。

## 判斷條件與後果

容量規劃要知道目前的負載離 saturation point 還有多遠。量過 saturation point 的系統，可以把實際 capacity 設在 knee point 以下、留出 headroom；沒有量過時，團隊不知道負載再增加多少就會進入 cliff，容量數字只是推測。saturation point 會隨架構與資料分布移動，hot partition 這類變化讓它在整體 capacity 還有餘時就提前出現，上一次量到的值因此可能已經不成立，所以每次重大改動後重新壓測，確認 knee 沒有往更低的負載移動。
