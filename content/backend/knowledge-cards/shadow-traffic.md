---
title: "Shadow Traffic"
date: 2026-05-12
description: "把 production traffic 複製到新版本驗證、但不返回結果給用戶的測試模式"
weight: 233
---

Shadow traffic 的核心概念是「production traffic 同時送到舊版本跟新版本、但只把舊版本的結果返回用戶、新版本的結果只用來驗證」。用戶感受不變、新版本實測 production load。可先對照 [Dark Launch](/backend/knowledge-cards/dark-launch/)。

## 概念位置

Shadow traffic 跟 [shadow read](/backend/knowledge-cards/shadow-read/) 不同 — shadow read 是 DB 層 replica；shadow traffic 是 application 層 traffic mirror。實作方法：GoReplay、service mesh shadow（Istio mirror）、AWS VPC Traffic Mirroring、自管 reverse proxy with mirror config。可先對照 [Dark Launch](/backend/knowledge-cards/dark-launch/)。

## 可觀察訊號與例子

需要 shadow traffic 的訊號是「想驗證新架構是否能撐 production load、但不能讓用戶受影響」。對應案例：[Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — pre-event 壓測但走 staging；real shadow 則是 production-traffic-driven。

## 設計責任

Shadow traffic 也消耗 production 下游資源（DB write、API call、external service）— 必須算進容量。如果新版本寫入會影響真實狀態（payment、order），必須設計成 *dry-run* 或寫入 isolated sandbox。Shadow 通常跑 1-7 天看 long-tail 訊號、不是 30 分鐘就下結論。
