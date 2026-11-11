---
title: "Shadow Traffic"
date: 2026-05-12
description: "把 production traffic 複製到新版本驗證、但不返回結果給用戶的測試模式"
weight: 234
---

Shadow traffic 的核心概念是「production traffic 同時送到舊版本跟新版本、但只把舊版本的結果返回用戶、新版本的結果只用來驗證」。用戶感受不變、新版本實測 production load。可先對照 [Dark Launch](/backend/knowledge-cards/dark-launch/)。

## 跟其他概念的關係

Shadow traffic 跟 [shadow read](/backend/knowledge-cards/shadow-read/) 不同 — shadow read 是 DB 層 replica；shadow traffic 是 application 層 traffic mirror。實作方法：GoReplay、service mesh shadow（Istio mirror）、AWS VPC Traffic Mirroring、自管 reverse proxy with mirror config。可先對照 [Dark Launch](/backend/knowledge-cards/dark-launch/)。

## 可觀察訊號與例子

需要 shadow traffic 的訊號是「想驗證新架構是否能撐 production load、但不能讓用戶受影響」。對應案例：[Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — pre-event 壓測但走 staging；real shadow 則是 production-traffic-driven。

## 判斷條件與後果

送到新版本的 shadow 請求是真實的 production 請求，它們觸發的下游呼叫（DB write、API call、external service）也打在真實的 production 資源上；容量規劃沒有算進這份流量時，下游在 shadow 期間的負載超過預估。新版本的寫入會改變真實狀態時（payment、order），同一筆請求被舊版本與新版本各處理一次，結果是重複扣款或重複建單，所以這類寫入在新版本設計成 *dry-run*，或導向 isolated sandbox。Long-tail 訊號（低頻的錯誤路徑、特定時段才出現的流量型態）在 30 分鐘的 shadow 裡出現的次數太少，判斷不了新版本在它們上面的行為，所以 shadow 通常跑 1-7 天。
