---
title: "Little's Law"
date: 2026-05-12
description: "說明系統內並發數、到達率與逗留時間三者的數學關係"
weight: 221
---

Little's Law 的核心概念是「穩態系統內、平均並發 = 到達率 × 平均逗留時間（L = λW）」。三個變數固定兩個就能推第三個、是容量規劃最小的數學工具。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 跟其他概念的關係

Little's Law 連接「業務需求」跟「系統參數」。給定預期 RPS（λ）跟 SLO latency 上限（W）、能算出系統最大同時並發數（L）；反過來、給定 connection pool size（L）跟 latency 目標、能算出可支撐的 RPS。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

需要用 Little's Law 反推的訊號是「不知道該訂多少 connection pool、thread pool、async worker」。例如：付款 API 預期 1000 RPS、SLO 是 p99 < 200ms、那麼穩態並發 ≈ 1000 × 0.2 = 200、connection pool 至少 200 + headroom。

## 判斷條件與後果

Little's Law 的三個量都是長時間的平均值，只在穩態（steady state）下成立：系統還在 warmup，或流量處在 burst 的過渡期時，到達率與逗留時間都在變動，用 L = λW 算出的並發數不代表任何一個時刻的實際值。網路、應用、DB 各 stage 各自處在穩態時，每一個 stage 都可以獨立套用，算出的各段逗留時間就是 latency budget 分解的依據。

同一條式子倒過來讀是故障診斷的工具：配額被誰佔走由 λW 決定，而 W 的跨度（毫秒到永不歸還）遠大於 λ 的跨度，因此佔用量的排序多半由逗留時間主導、而報錯的位置只跟到達率有關。這兩者分屬不同元件時的歸因順序見 [配額耗盡的症狀落在申請最頻繁的元件、成因在持有最久的那個](/report/resource-exhaustion-symptom-vs-holder/)。
