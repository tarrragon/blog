---
title: "Cascading Failure"
date: 2026-04-23
description: "說明局部故障如何透過等待、重試與資源耗盡擴散到整個系統"
weight: 51
---


Cascading failure 的核心概念是「局部故障沿著依賴關係擴散成更大範圍故障」。常見擴散路徑包括 timeout 太長、重試太多、connection pool 耗盡、queue 堆積、thread pool 被占滿與 fallback 過載。 可先對照 [Certificate Chain and Trust Root](/backend/knowledge-cards/certificate-chain-trust/)。

## 概念位置

Cascading failure 是可靠性設計的主要防護目標。Timeout、backpressure、rate limit、circuit breaker、bulkhead 與 load shedding 都是在切斷擴散路徑。 可先對照 [Certificate Chain and Trust Root](/backend/knowledge-cards/certificate-chain-trust/)。

## 可觀察訊號與例子

系統需要防 cascading failure 的訊號是原始故障在一個服務，症狀卻出現在多個上游。資料庫變慢後，API worker 卡住、queue lag 上升、retry 增加，最後登入與 checkout 都變慢。

## 設計責任

防護要從依賴圖出發，為每個下游設定 timeout、pool limit、重試預算與降級策略。Incident 後應檢查故障是如何跨服務擴散，而不只修復第一個壞掉的元件。
