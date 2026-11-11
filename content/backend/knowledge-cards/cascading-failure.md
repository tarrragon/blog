---
title: "Cascading Failure"
date: 2026-04-23
description: "說明局部故障如何透過等待、重試與資源耗盡擴散到整個系統"
weight: 52
---

Cascading failure 的核心概念是「局部故障沿著依賴關係擴散成更大範圍故障」。常見擴散路徑包括 timeout 太長、重試太多、connection pool 耗盡、queue 堆積、thread pool 被占滿與 fallback 過載。 可先對照 [Certificate Chain and Trust Root](/backend/knowledge-cards/certificate-chain-trust/)。

## 跟其他概念的關係

Cascading failure 是可靠性設計的主要防護目標。Timeout、backpressure、rate limit、circuit breaker、bulkhead 與 load shedding 都是在切斷擴散路徑。跟 [Correlated Failure](/backend/knowledge-cards/correlated-failure/) 的差別：cascading 是「一個壞了逐級傳導放大」（有先後），correlated 是「共享觸發器讓多個同時壞」（無先後）。故障在觸發消失後仍延續的那一種是 [Metastable Failure](/backend/knowledge-cards/metastable-failure/)；它的持續效應也會擴散到沒碰到觸發的元件，所以兩者可以同時發生。範圍從一個實例擴大到上游的過程，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)〈影響範圍：從單一 key 到依賴與上游〉。

## 可觀察訊號與例子

系統需要防 cascading failure 的訊號是原始故障在一個服務，症狀卻出現在多個上游。資料庫變慢後，API worker 卡住、queue lag 上升、retry 增加，最後登入與 checkout 都變慢。

## 判斷條件與後果

Cascading failure 沿依賴圖擴散，哪一條依賴缺了防護，故障就從那一條傳到上游。對某個下游沒有 timeout 時，下游一變慢，上游的 worker 跟著卡住；沒有 pool limit 時，一個慢的下游佔滿共用的 connection pool，其他下游的呼叫也拿不到連線；沒有重試預算時，下游越慢重試越多，原本的故障被放大；沒有降級策略時，非必要的下游失敗也讓整個請求失敗。Incident 後只修復第一個壞掉的元件時，擴散路徑原封不動，下一次換一個元件故障，會沿同一條路徑擴散，所以事後檢討追查故障如何跨服務擴散。
